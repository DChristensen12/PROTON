"""Shared fakes (devices) and fixtures for the suite, so that no test needs a real device to be plugged in for testing"""

import pytest
from proton.Hardware.Detectors.geiger_counts.readout import RawSample


# Captured off a real detector (the GC-01), so tests against these replies match what the device actually sends
REAL_REPLIES = {
    "GET deviceId": [b"OK FNIRSI GC-01 (CH32F103C8);Rad Pro 3.1.1/en;51003200080000484e52544e\r\n"], "GET tubePulseCount": [b"OK 26928\r\n"],
    "GET tubeRate": [b"OK 19.152\r\n"]
}

class FakeSerial:
    """Stand in for a pyserial port, returning canned bytes for each command and keeping what was sent"""

    def __init__(self, replies = None):
        self.replies = dict(replies) if replies else {}
        self.is_open = True
        self.written = []
        self._pending = []

    def __enter__(self):
        """Let the fake be used in a with block"""
        return self

    def __exit__(self, *exc):
        """Close on the way out, matching the real serial context manager"""
        self.close()

    def reset_input_buffer(self):
        """Drop whatever reply is queued, like the real port discarding its buffer"""
        self._pending = []

    def write(self, data):
        """Record the command and queue its reply"""
        command = data.decode("ascii").strip()
        self.written.append(command)
        reply = self.replies.get(command, [b"ERROR\r\n"])  # an unknown command reads as a device error
        if callable(reply):
            reply = reply()  # this allows a test to grow the reply in between calls
        self._pending = list(reply) if isinstance(reply, list) else [reply]

    def readline(self):
        """Returns the next pending line, or empty bytes to simulate a timeout; tests that a 
        timeout occurs in FakeSerial when we want it to"""
        if self._pending:
            return self._pending.pop(0)
        return b""

    def close(self):
        """Mark the port closed, mirroring pyserial's close"""
        self.is_open = False


class FakeDevice:
    """Tests that record_device can be tested alone via having a serial-free stand-in device"""

    DEFAULT_PORT = "/dev/fake"
    DEFAULT_POLL_INTERVAL = 0.0
    last = None  # the most recent instance built, so a test can inspect it

    def __init__(self, port = None, stop_after = 3):
        FakeDevice.last = self
        self.port = port
        self.closed = False
        self.stop_after = stop_after
        self._n = 0   # how many samples returned so far

    def __enter__(self):
        """Let the fake be used in a with block"""
        return self

    def __exit__(self, *exc):
        """Mark closed on the way out"""
        self.closed = True

    def get_device_id(self):
        """Return a fixed label, since no real hardware is behind this fake"""
        return "fake device"

    def read_raw_sample(self):
        """Return samples until stop_after, then raise like a device that dropped off the bus"""
        if self._n >= self.stop_after:
            raise OSError("fake device dropped off")
        self._n += 1
        return RawSample(pulse_count = self._n, tube_rate = 1.0, wall_time = 0.0, monotonic = 0.0)

@pytest.fixture
def real_replies():
    """Return the captured real device replies"""
    return REAL_REPLIES


@pytest.fixture
def fake_serial():
    """Return the FakeSerial class to build whatever replies a test needs"""
    return FakeSerial


@pytest.fixture
def fake_device():
    """Return the FakeDevice class, clearing last so nothing crosses between tests"""
    FakeDevice.last = None
    return FakeDevice


@pytest.fixture
def sample_csv(tmp_path):
    """Write one small valid counts csv and return its folder for the replay side"""
    (tmp_path / "run.csv").write_text(
        "pulse_count,tube_rate,wall_time,monotonic\n"
        "10,20.0,1000.0,5.0\n"
        "11,21.0,1001.0,6.0\n"
    )
    return tmp_path
