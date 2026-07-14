"""
readout.py holds the pulse sources for geiger_pulses.
 
A counter hands back a rate whenever we ask for one. This device only speaks when a particle shows up,
so a read waits on the next pulse instead of sampling on a clock. That is why the recorder runs with a
poll interval of zero here.
 
EspPulseDevice is the ESP32 I used in my own setup. It is one way in, not the only one.
GeneralPulsesDevice takes intervals from wherever they come from, whether that is a csv I recorded, a
series I generated, or a reader I wrote for some other board.
"""


import time
from pathlib import Path
from typing import NamedTuple
from proton.common.exceptions import ProtonError
from proton.common.data_handler import PulseTrain


class RawPulse(NamedTuple):
    """One detected pulse and the gap in microseconds since the pulse before it"""
    pulse_index: int
    dt_us: int
    wall_time: float
    monotonic: float

class PulseError(ProtonError):
    """Raised when a pulse source cannot be opened, read, or parsed

        Carries optional context about the pulse source that failed, so a handler or a
    traceback can see what was happening without re-deriving it. All fields default
    to None, so the plain PulseError("message") form still works at every existing
    raise site.
    """

    def __init__(self, message, source = None, raw = None, path = None):
        """
        The __init__ here keeps the failure context on the error. This is so that the source names the device or replay
        (the esp32 port or a device_id), and raw is the offending serial line when a read would not parse, path is the csv when the failure was a load.
        """
        super().__init__(message)
        self.source = source   # esp32:<port> or the general device's device_id
        self.raw = raw         # the exact line that would not parse, when there was one
        self.path = path       # the csv involved, when the failure was a load

    def __str__(self):
        """Messages first, then whatever context is set, so on its own, the traceback can be read"""
        parts = [self.message]
        if self.source is not None:
            parts.append("source=" + str(self.source))
        if self.path is not None:
            parts.append("path=" + str(self.path))
        if self.raw is not None:
            parts.append("raw=" + repr(self.raw))
        return " | ".join(parts)


class EspPulseDevice:
    """Reads per pulse intervals off an ESP32 running the ggreg20_pulse_timer sketch"""

    DEFAULT_PORT = "/dev/ttyUSB0"
    DEFAULT_POLL_INTERVAL = 0.0   # pulses set their own pace, so the recorder must not sleep between reads
    DEFAULT_BAUD = 115200

    def __init__(self, port = None, baud = None, timeout = 1.0, serial_port = None):
        """Opens the serial link, or takes an already open one so tests can inject a fake one.

        pyserial asserts DTR and RTS the moment a port opens. On this DevKit those lines are
        wired to EN and GPIO0, so a plain open reboots the chip and dumps ROM bootloader garbage
        into the stream. Building the Serial object unopened and clearing dtr and rts before
        calling open() avoids that reset. dsrdtr in the constructor does not, since it is a
        different pair of lines.
        """
        self.port = port or self.DEFAULT_PORT
        self.baud = baud or self.DEFAULT_BAUD
        self._last_index = None   # nothing read yet, so the first index has nothing to be checked against
        if serial_port is not None:
            self._serial = serial_port
            return
        import serial  # we would only need this installed for a real device path
        self._serial = serial.Serial()
        self._serial.port = self.port
        self._serial.baudrate = self.baud
        self._serial.timeout = timeout
        self._serial.dtr = False
        self._serial.rts = False
        try:
            self._serial.open()
        except serial.SerialException as err:
            raise PulseError("could not open " + str(self.port)) from err
        time.sleep(0.1)   # lets the line settle before WE clear it
        self._serial.reset_input_buffer()   # discards anything that arrived before the first real read

    def get_device_id(self):
        """A label for the csv header, since the board reports no serial number of its own"""
        return "esp32:" + str(self.port)

    def read_raw_pulse(self):
        """Wait for the next interval and stamp it with the host clocks.

        A quiet line is normal. At background the tube may go seconds between pulses, so a read
        that times out just goes around again rather than ending the run.

        The board's index counts up by construction, so a repeat or a drop back is not a fluke
        of the data, it is a stale read. I raise rather than write it, since that once flooded a
        csv with thousands of duplicate rows before anything downstream noticed.

        I read with read_until rather than readline. readline is inherited from io.IOBase and
        can hand back a partial line when the timeout fires mid line. read_until is pyserial's
        own implementation, and only returns on the terminator or the timeout.
        """
        while True:
            line = self._serial.read_until(b"\n")
            if not line:
                continue   # nothing arrived before the serial timeout, so keep waiting
            text = line.decode("utf-8", errors = "replace").strip()
            # the sketch prints a banner on boot, so I skip anything that is not two numbers
            if text == "" or text.startswith("#"):
                continue
            cells = text.split()
            if len(cells) != 2:
                continue
            try:
                index = int(cells[0])
                dt_us = int(cells[1])
            except ValueError:
                continue
            if self._last_index is not None and index <= self._last_index:
                raise PulseError("pulse index did not advance: previous " + str(self._last_index) + ", received " + str(index))
            self._last_index = index
            return RawPulse(index, dt_us, time.time(), time.monotonic())

    def close(self):
        """Release the serial port"""
        self._serial.close()

    def __enter__(self):
        """Let the device be used in a with block"""
        return self

    def __exit__(self, exc_type, exc, tb):
        """Close the port on the way out even if the body raised"""
        self.close()
        return False


class GeneralPulsesDevice:
    """A pulse source that does not care where the intervals come from.

    EspPulseDevice speaks one board over one serial format. This one takes any source of delta t in
    microseconds, so a csv, a synthetic series, or somebody else's hardware all reach the recorder
    through the same door. Build it with one of the three constructors below rather than calling
    __init__ directly.
    """

    DEFAULT_POLL_INTERVAL = 0.0

    def __init__(self, read_dt, device_id = "general", intervals = None):
        """Take a zero argument callable that returns the next interval in microseconds.

        intervals holds the values when the source is already in memory, which is what lets
        replace_dt_us and len work. A streaming source leaves it None.
        """
        self._read_dt = read_dt
        self._device_id = device_id
        self._intervals = intervals
        self._index = 0

    @classmethod
    def from_intervals(cls, values, device_id = "intervals"):
        """Replay a series I already have, like samples drawn from the diffusion model"""
        values = [int(v) for v in values]
        return cls(cls._cursor(values), device_id = device_id, intervals = values)

    @classmethod
    def from_csv(cls, path, device_id = "replay"):
        """Replay a recorded run, from a csv directly or the one csv inside a folder"""
        values = cls._load(Path(path))
        return cls(cls._cursor(values), device_id = device_id, intervals = values)

    @classmethod
    def from_reader(cls, read_one, device_id = "reader"):
        """Wrap hardware PROTON has never heard of.

        read_one takes no arguments and returns the next interval in microseconds. That is the whole
        contract, so a new detector needs a few lines here rather than a new class.
        """
        return cls(read_one, device_id = device_id)

    @staticmethod
    def _cursor(values):
        """Turn a list into a callable that hands back one value per call"""
        state = {"i": 0}

        def read_dt():
            """Return the next stored interval, or say so when there are none left"""
            if state["i"] >= len(values):
                raise PulseError("no intervals left to replay")
            dt = values[state["i"]]
            state["i"] += 1
            return dt

        return read_dt

    def get_device_id(self):
        """Answer like the esp32 device so the recorder cannot tell the two apart"""
        return self._device_id

    def read_raw_pulse(self):
        """Pull the next interval from the source and stamp it with the host clocks"""
        dt_us = int(self._read_dt())
        self._index += 1
        return RawPulse(self._index, dt_us, time.time(), time.monotonic())

    def replace_dt_us(self, values):
        """Swap in a synthetic series, to check a model against a distribution I already know"""
        if self._intervals is None:
            raise PulseError("this source streams, so there is nothing held in memory to replace")
        if len(values) != len(self._intervals):
            raise PulseError("gave " + str(len(values)) + " values for " + str(len(self._intervals)) + " rows")
        self._intervals = [int(v) for v in values]
        self._read_dt = self._cursor(self._intervals)
        self._index = 0   # start the replay over so the new values read from the top

    @staticmethod
    def _load(path):
        """Read the dt_us column out of a csv, either a file directly or the one csv inside a folder"""
        if path.is_dir():
            files = sorted(path.glob("*.csv"))
            if not files:
                raise PulseError("no csv to load in " + str(path))
            path = files[0]
        values = []
        with path.open() as f:
            header = f.readline().strip().split(",")
            if "dt_us" not in header:
                raise PulseError("no dt_us column in " + str(path))
            column = header.index("dt_us")
            for line in f:
                line = line.strip()
                if line == "":
                    continue
                values.append(int(line.split(",")[column]))
        return values

    def to_train(self, **kwargs):
        """Hands the held intervals over as a PulseTrain, the door from this device into the
        analysis side. It converts the microsecond gaps to seconds and hands over the whole
        stored series regardless of how far a replay has read. There is no wall clock behind
        stored intervals, so t0 stays None unless the caller passes one."""
        if self._intervals is None:
            raise PulseError("this source streams, record it to a csv first and load that")
        if "detector_id" not in kwargs:
            kwargs["detector_id"] = self._device_id
        return PulseTrain.from_intervals([dt / 1_000_000 for dt in self._intervals], **kwargs)

    def close(self):
        """Here so this device closes like the serial one"""
        return None

    def __enter__(self):
        """Let the device be used in a with block"""
        return self

    def __exit__(self, exc_type, exc, tb):
        """Nothing to release, but I keep the shape of the serial device"""
        return False

    def __len__(self):
        """How many stored intervals are still waiting. A streaming source has no answer to give"""
        if self._intervals is None:
            raise PulseError("this source streams, so its length is not known")
        return max(0, len(self._intervals) - self._index)
    