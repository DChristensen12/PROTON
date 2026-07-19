# Tests for record_pulses.py, run against a fake device with record_samples patched out, so no
# board is needed and no serial port opens.

from proton.Hardware.Detectors.geiger_pulses import record_pulses


class FakeEsp:
    """Stands in for EspPulseDevice, recording how it was built"""

    DEFAULT_POLL_INTERVAL = 0.0
    last = None

    def __init__(self, port = None):
        """Stores a reference to itself so a test can check the port it was given"""
        FakeEsp.last = self
        self.port = port

    def __enter__(self):
        """Opens in a with block"""
        return self

    def __exit__(self, *exc):
        """Nothing to release"""
        return False

    def get_device_id(self):
        """Stand in id"""
        return "fake esp"

    def read_raw_pulse(self):
        """Never called, record_samples is patched out in these tests"""
        raise AssertionError("should not be read in these tests")


class TestRecord:
    """Tests that record wires the device into the shared recorder the right way"""

    def test_passes_poll_interval_zero(self, tmp_path, monkeypatch):
        """Pulses set their own pace, so a sleep between reads would corrupt dt. This pins the zero."""
        captured = {}
        monkeypatch.setattr(record_pulses, "EspPulseDevice", FakeEsp)
        monkeypatch.setattr(record_pulses, "record_samples", lambda **kw: captured.update(kw) or 0)
        record_pulses.record(out_dir = tmp_path)
        assert captured["poll_interval"] == 0.0

    def test_builds_the_output_path(self, tmp_path, monkeypatch):
        """out_dir and name should come together as out_dir/name.csv"""
        captured = {}
        monkeypatch.setattr(record_pulses, "EspPulseDevice", FakeEsp)
        monkeypatch.setattr(record_pulses, "record_samples", lambda **kw: captured.update(kw) or 0)
        record_pulses.record(name = "myrun", out_dir = tmp_path)
        assert captured["out_path"] == tmp_path / "myrun.csv"

    def test_forwards_the_port(self, tmp_path, monkeypatch):
        """A port passed to record should reach the device it opens"""
        monkeypatch.setattr(record_pulses, "EspPulseDevice", FakeEsp)
        monkeypatch.setattr(record_pulses, "record_samples", lambda **kw: 0)
        record_pulses.record(out_dir = tmp_path, port = "/dev/xyz")
        assert FakeEsp.last.port == "/dev/xyz"
        