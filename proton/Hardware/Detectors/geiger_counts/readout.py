# Everything for linking to a geiger counter that reports a running pulse count, and pulling its raw data in.

import csv
import time
from typing import NamedTuple
from pathlib import Path
import proton
from proton.common import ProtonError
from proton.common.data_handler import CountSeries


class RawSample(NamedTuple):
    """Pulls one raw reading off a device, stampled with when it is read"""
    pulse_count: int # the running total of pulses the tube has counted, the real raw signal
    tube_rate: float # the rate the device reports itself in cpm
    wall_time: float # unix time
    monotonic: float # a clock that never jumps back, used for intervals


class GeneralCountsDevice:
    """ This is the General Geiger Counts Device Class. It is for when you want to use
    a custom hardware setup within PROTON or to use no hardware.

    There are two ways to use this class:
        1.) Use alternative hardware: store data here to easily integrate your own setup with PROTON
        2.) Use no hardware: use the default settings to use data already stored in PROTON package.

    You can either use the stored count samples (by default for a non-hardware option)
    or give it samples, as the same RawSample type RadProDevice produces.
    """

    # Uses default data by default.
    DEFAULT_DATA_DIR = Path(proton.__file__).resolve().parent / "default_data" / "geiger_counts"

    # The four data columns that would need to be matching the fields on RawSample
    FIELDS = ("pulse_count", "tube_rate", "wall_time", "monotonic")

    DEFAULT_POLL_INTERVAL = 1.0  # I copied this from RadProDevice, so record_device needs no override to run this class

    __slots__ = ("_samples", "_cursor", "_reader", "_device_id")

    def __init__(self, data_dir = None, reader = None, device_id = None, samples = None):
        """Starts empty, then loads in whatever count data lives in data_dir

        Note: If data_dir is left out, this will automatically fall back to the
        example data bundled with the package. If that folder is missing or empty,
        it'll stay empty rather than crash, so building the device is always safe to do.
        You'd be able to fill it later by loading a dataset or by replacing fields one at a time.

        If reader is given instead, this becomes a live device: read_raw_sample calls
        reader() for each sample rather than replaying stored data. device_id then names
        that hardware for get_device_id. This is how from_readers builds a live device.

        samples takes a list of RawSample built elsewhere, straight into memory with no file
        involved. This is how from_samples builds a device.
        """

        self._samples = [] # one list of RawSample, so adding a field means touching RawSample and nothing else
        self._cursor = 0 # The stored row read_raw_sample hands back next
        self._reader = reader
        self._device_id = device_id
        if reader is not None:
            return
        if samples is not None:
            self._load_samples(samples)
            return
        data_dir = data_dir if data_dir is not None else self.DEFAULT_DATA_DIR
        self.load(data_dir)

    def __enter__(self):
        """Lets you use the device in a with block"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Nothing to release, but I keep the shape of RadProDevice"""
        return False

    def load(self, data_dir):
        """
        Load every csv in data_dir into the replay list, in sorted filename order
        Reads by column name off each header, so order of columns in the file does
        not matter as long as the four RawSample fields are present. A missing folder
        is treated as no data rather than an error, so that keeps the default path
        safe even before we've recorded anything.
        """

        data_dir = Path(data_dir)
        if not data_dir.is_dir():
            return # This means there is nothing to load yet, so stay as is

        # clears first, so that calling load twice swaps datasets instead of stacking them
        self._samples = []
        self._cursor = 0

        for path in sorted(data_dir.glob("*.csv")):
            self._read_file(path)

    def _load_samples(self, samples):
        """Fills the replay list from an iterable of RawSample and rewinds. This is the in
        memory counterpart to load(), so a device built from already read samples replays them
        exactly like one built from a csv."""
        self._samples = [
            RawSample(
                pulse_count = int(s.pulse_count),
                tube_rate = float(s.tube_rate),
                wall_time = float(s.wall_time),
                monotonic = float(s.monotonic),
            )
            for s in samples
        ]
        self._cursor = 0

    def _read_file(self, path):
        """
            Pulls every row out of one csv and appends it onto the columns
            We check that the header has all four fields at the start so that a
            malformed file fails sooner rather than later with its own name instead of
            dropping data.
        """

        with path.open(newline = "") as f:
            reader = csv.DictReader(f)
            missing = [field for field in self.FIELDS if field not in (reader.fieldnames or [])]
            if missing:
                raise ValueError("file " + str(path) + " is missing the columns: " + ", ".join(missing))
            for row in reader:
                self._samples.append(RawSample(
                    pulse_count = int(row["pulse_count"]),
                    tube_rate = float(row["tube_rate"]),
                    wall_time = float(row["wall_time"]),
                    monotonic = float(row["monotonic"]),
                ))

    def read_raw_sample(self):
        """Hands back the next stored sample as RawSample, then steps the cursor"""
        if self._reader is not None:
            return self._reader()
        if self._cursor >= len(self._samples):
            if len(self._samples) == 0:
                raise ValueError("no count data loaded to replay")
            raise ValueError("replay is done and dusted, call reset() to start over")

        i = self._cursor
        self._cursor += 1
        return self._samples[i]

    def reset(self):
        """Rewind to the first stored sample, so that we can replay the entire set again."""
        self._cursor = 0

    def get_device_id(self):
        """A stand in id, so the code that records which device it used still gets ananswer."""
        if self._device_id is not None:
            return self._device_id
        if self._reader is not None:
            return "GeneralCountsDevice live"
        return "GeneralCountsDevice replay (" + str(len(self)) + " samples)"

    def replace_pulse_count(self, values):
        """Swaps the pulse_count column for your own values, leaving the other fields unchanged"""
        self._replace_column("pulse_count", values, int)

    def replace_tube_rate(self, values):
        """Swaps the tube_rate column for your own values, leaving the other fields alone"""
        self._replace_column("tube_rate", values, float)

    def replace_wall_time(self, values):
        """Swaps the wall_time column for your own values, leaving the other fields unchanged"""
        self._replace_column("wall_time", values, float)

    def replace_monotonic(self, values):
        """Swaps the monotonic column for your own values, leaving the other fields unchanged"""
        self._replace_column("monotonic", values, float)

    def _replace_column(self, field, values, cast):
        """
        The one place a column swap actually happens, the replace_ methods above just
        name the field and its cast. Replacing a field only makes sense against data that
        already has a length, so we check the new column against the rows already being held.
        The cast keeps the stored types matching what the RadProDevice class would have produced,
        and _replace on the namedtuple keeps every other field untouched.
        """
        values = [cast(v) for v in values]
        current = len(self)
        if current == 0:
            raise ValueError("load a dataset before replacing the " + field + " field")
        if len(values) != current:
            raise ValueError("the new " + field + " column has " + str(len(values)) + " values but the dataset has " + str(current) + " rows")
        self._samples = [s._replace(**{field: v}) for s, v in zip(self._samples, values)]

    def __len__(self):
        """How many stored samples is being held in the moment this is called

        A live reader gives me no stored rows to count, so I raise here rather than
        answer 0, which would look like an empty replay instead of a stream.
        """
        if self._reader is not None:
            raise ValueError("this source streams, so its length is not known")
        return len(self._samples)

    def to_series(self, **kwargs):
        """Hands the held samples over as a CountSeries, the door from this device into the
        analysis side. pulse_count is cumulative, so the series differences it into counts per
        interval, with times off monotonic relative to the first sample and t0 off its wall_time.
        The device's own cpm estimate stays behind, the series derives rates from raw counts."""
        if self._reader is not None:
            raise ValueError("this source streams, record it to a csv first and load that")
        if "detector_id" not in kwargs:
            kwargs["detector_id"] = self.get_device_id()
        if ("t0" not in kwargs or kwargs["t0"] is None) and self._samples:
            kwargs["t0"] = self._samples[0].wall_time
        rel = [s.monotonic - self._samples[0].monotonic for s in self._samples] if self._samples else []
        return CountSeries.from_cumulative(rel, [s.pulse_count for s in self._samples], **kwargs)

    @classmethod
    def from_samples(cls, samples, device_id = None):
        """Builds a device straight from RawSample objects you built yourself, whatever device
        they came from. Parse your own file however you like into RawSample, hand me the list,
        and it replays like any other. This is the in memory door, for when you already have the
        data and do not want to round trip it through a csv first.
        """
        return cls(samples = list(samples), device_id = device_id)

    @classmethod
    def from_readers(cls, read_pulse_count, read_tube_rate, device_id = None):
        """
        from_readers builds a live device from your own per field read functions, for the purpose of
        pulling samples off hardware as it runs. If you already have data in memory (stored somewhere),
        then you'd use the replace_ methods instead, and toreplay data from files, just use the default loading path.

        you write one function per field that is yours to read:
            read_pulse_count: takes no arguments, returns an int, the running cumulative pulse total
            read_tube_rate: takes no arguments, returns a float, the rate in counts per minute
        device_id is an optinal string naming your hardware.

        PROTON stam[s wall_time and monotonic itself, and will cast your two reads to those types,
        so the sample always comes out in the exact shape the redorder and the reply device expect.

        TLDR: If you use alternative hardware, you can use this to ensure it easily works within PROTON
        """
        def reader():
            wall_time = time.time()
            monotonic = time.monotonic()
            return RawSample(
                pulse_count = int(read_pulse_count()),
                tube_rate = float(read_tube_rate()),
                wall_time = wall_time,
                monotonic = monotonic
            )
        return cls(reader = reader, device_id = device_id)


class RadProDevice:
    """ Wrapper around the Rad Pro serial protocol. It opens the serial port, sends
    the GET commands, and hands back the device id, the running pulse count, the tube rate,
    and the timestamped raw samples."""

    DEFAULT_PORT = "/dev/ttyACM0" # This is where GC-01 lands on my machine, could also be /dev/ttyACM0
    BAUD_RATE = 115200 # pyserial asks for one of these, so we use the value from the firmware documents
    SERIAL_TIMEOUT = 2.0 # how long one read waits before I'd call the device silent, in seconds
    DEFAULT_POLL_INTERVAL = 1.0 #how often the logger polls the cumulative pulse count, in seconds
    FALLBACK_SENSITIVITY_CPM_PER_USVH = 153.8 # M4011 tube sensitivity in cpm per uSv/h. Used as a display fallback when the device cannot report its own calibrated valye.

    __slots__ = ("_port_name", "_serial")

    def __init__(self, port = None, baud = None, timeout = None, serial_port = None):
        """
        Opens the serial port to the device, or use a port object passed in.
        We fall back to the class defaults when the caller leaves an argument out.
        """

        port = port if port is not None else self.DEFAULT_PORT
        baud = baud if baud is not None else self.BAUD_RATE
        timeout = timeout if timeout is not None else self.SERIAL_TIMEOUT
        self._port_name = port
        if serial_port is not None:
            self._serial = serial_port # Use object handed to it
        else:
            import serial  # I only need this installed for the real device path
            self._serial = serial.Serial(port, baudrate = baud, timeout = timeout)

    def __enter__(self):
        """Lets you use the device in a with block"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Always close the port on the way out, even when something has failed."""
        self.close()

    def close(self):
        """Closes the serial port if it still open when called"""
        if self._serial is not None and self._serial.is_open:
            self._serial.close()

    def _command(self, command):
        """Sends one command and returns the raw text the device replies with.

        The device could possibly send a stray blank line, not sure if it prefixes
        replies with OK, so I handle both and let the peek function below show me the real format."""

        # We clear anything sitting in the buffer first so an old reply cannot bleed into this one.
        self._serial.reset_input_buffer()
        self._serial.write((command + "\n").encode("ascii"))

        for _ in range(4):
            line = self._serial.readline().decode("ascii", errors = "replace").strip()
            if line == "":
                continue # that means there is a stray blank line, so read the next one
            if line.startswith("ERROR"):
                raise RadProError("device returned:" + line)
            if line == "OK":
                continue # the valye is on the next line, so keep reading
            if line.startswith("OK "):
                return line[3:].strip() # drop the OK prefix and keep the value
            return line
        raise RadProError("no usable response to command: " + command)

    def get_device_id(self):
        """Asks the device who it is to confirm we are talking to the right one"""
        return self._command("GET deviceId")

    def get_pulse_count(self):
        """Reads the running total of pulses the tube has counted thus far"""
        return int(self._command("GET tubePulseCount"))

    def get_tube_rate(self):
        """Reads the rate the device reports for itself, in counts per minute"""
        return float(self._command("GET tubeRate"))

    def read_raw_sample(self):
        """
        Pulls one timestamped raw sample off the device.

        We grab both clocks first, so the timestamps sit as close as it could be to
        the actual read, then pull the count and device rate.
        """
        Wall_time = time.time()
        Monotonic = time.monotonic()
        Pulse_count = self.get_pulse_count()
        Tube_rate = self.get_tube_rate()
        return RawSample(pulse_count = Pulse_count, tube_rate = Tube_rate, wall_time = Wall_time, monotonic = Monotonic)


class RadProError(ProtonError):
    """If the device says ERROR, went quiet, or  sends something I cannot parse."""

    def __init__(self, message, command = None, raw = None):
        """We keep the failed command and the raw reply on the error to examine what went wrong"""
        super().__init__(message)
        self.command = command # the command that triggered the failure
        self.raw = raw # Whatever the device sends back

# Public Functions
def show_raw_replies(port = None, commands = None): # Function for devices with Rad Pro flashed on it
    """
    Opens the device and prints the raw bytes it sends back for a few commands
    This is used as a quick way to confirm whether a Rad Pro device is connected and to see the exact
    shape of its replies. This helps when something isn't parsing the way you'd expect.
    It opens its own connection, so you do not need to build a RadProDevice first.
    """
    import serial  # I only need this for talking to real RadPro hardware
    port = port if port is not None else RadProDevice.DEFAULT_PORT
    # we default to the three commands the rest of the pipeline leans on
    if commands is None:
        commands = ["GET deviceId", "GET tubePulseCount", "GET tubeRate"]
    with serial.Serial(port, RadProDevice.BAUD_RATE, timeout = RadProDevice.SERIAL_TIMEOUT) as s:
        time.sleep(0.2) # lets the port settle, some usb stacks reset the device on connection
        s.reset_input_buffer()
        for command in commands:
            s.write((command + "\n").encode("ascii"))
            #repr shows the exact bytes, including the Ok prefix and the trailing carriage reutnr
            print(command, "->", repr(s.readline()))

