# This holds any shared fakes and fixtures for the suite, so no test needs a real GC-01 plugged in. I got the real replies needed for this to work.

import pytest
from proton.Hardware.Detectors.geiger_counts.readout import RawSample


# These are some real GC-01 replies that were captured off the live device
REAL_REPLIES = {
    "GET deviceId": [b"OK FNIRSI GC-01 (CH32F103C8);Rad Pro 3.1.1/en;51003200080000484e52544e\r\n"],
    "GET tubePulseCount": [b"OK 26928\r\n"],
    "GET tubeRate": [b"OK 19.152\r\n"],
}

class FakeSerial:
    """Stand in for a pyserial port, answering commands with canned bytes and keeping what was sent"""

    def __init__(self, replies = None):
        """This just sets up the reply table and an empty record of writes"""
        self.replies = dict(replies) if replies else {}
        self.is_open = True
        self.written = []        # Every command we were handed
        self._pending = []       # Reply lines still waiting to be read

    def __enter__(self):
        """This lets it work in a with block"""
        return self

    def __exit__(self, *exc):
        """This closes on the way out"""
        self.close()

    def reset_input_buffer(self):
        """This one drops anything still pending"""
        self._pending = []

    def write(self, data):
        """This records the command and queues up its reply"""
        command = data.decode("ascii").strip()
        self.written.append(command)
        reply = self.replies.get(command, [b"ERROR\r\n"])   # an unknown command reads as a device error
        if callable(reply):
            reply = reply()      # lets a test grow the reply between calls
        self._pending = list(reply) if isinstance(reply, list) else [reply]

    def readline(self):
        """Hands back the next pending line, or empty bytes for a timeout"""
        if self._pending:
            return self._pending.pop(0)
        return b""

    def close(self):
        """marks the port shut"""
        self.is_open = False


class FakeDevice:
    """A serial free stand in device, so record_device can be tested alone. hands back samples until
    stop_after, then raises like a device that dropped off the bus"""

    DEFAULT_PORT = "/dev/fake"
    DEFAULT_POLL_INTERVAL = 0.0
    last = None                  # the most recent instance built, so a test can inspect it

    def __init__(self, port = None, stop_after = 3):
        """ This remembers itself as the last device and starts the sample counter at zero"""
        FakeDevice.last = self
        self.port = port
        self.closed = False
        self.stop_after = stop_after
        self._n = 0

    def __enter__(self):
        """opens in a with block"""
        return self

    def __exit__(self, *exc):
        """flags that it was closed"""
        self.closed = True

    def get_device_id(self):
        """stand in id"""
        return "fake device"

    def read_raw_sample(self):
        """climbs a sample until stop_after, then raises to mimic an unplug"""
        if self._n >= self.stop_after:
            raise OSError("fake device dropped off")
        self._n += 1
        return RawSample(pulse_count = self._n, tube_rate = 1.0, wall_time = 0.0, monotonic = 0.0)

@pytest.fixture
def real_replies():
    """This hands over the captured real replies"""
    return REAL_REPLIES


@pytest.fixture
def fake_serial():
    """This hands over the FakeSerial class to build whatever replies a test needs"""
    return FakeSerial


@pytest.fixture
def fake_device():
    """This hands over the FakeDevice class, clearing its last so nothing bleeds between tests"""
    FakeDevice.last = None
    return FakeDevice


@pytest.fixture
def sample_csv(tmp_path):
    """This writes one small valid counts csv and hands back its folder for the replay side"""
    (tmp_path / "run.csv").write_text(
        "pulse_count,tube_rate,wall_time,monotonic\n"
        "10,20.0,1000.0,5.0\n"
        "11,21.0,1001.0,6.0\n"
    )
    return tmp_path
