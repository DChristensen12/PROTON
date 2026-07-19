# Tests for the pulse smoke test. Its dead time report is what caught a real wiring fault, so the
# report itself is worth pinning (otherwise I never would have figurd out why the oriignal data was faulty). Runs against a fake device, no board.

import pytest
from proton.Hardware.Detectors.geiger_pulses import check_pulses
from proton.Hardware.Detectors.geiger_pulses.readout import RawPulse


class CannedEsp:
    """Returns a fixed list of dt_us values as pulses"""

    values = []   # a test sets this before building

    def __init__(self, port = None):
        """Takes a copy of the canned values so each build starts from the top"""
        self._values = list(type(self).values)
        self._n = 0

    def __enter__(self):
        """Opens in a with block"""
        return self

    def __exit__(self, *exc):
        """Nothing to release"""
        return False

    def get_device_id(self):
        """Stand in id"""
        return "canned"

    def read_raw_pulse(self):
        """Returns the next canned interval"""
        dt = self._values[self._n]
        self._n += 1
        return RawPulse(self._n, dt, 0.0, 0.0)


class TestCheck:
    """Tests for the rate line and the dead time report"""

    def test_returns_the_intervals_and_reports_the_rate(self, monkeypatch, capsys):
        """The intervals should come back as read, and the printed rate should match their spacing"""
        CannedEsp.values = [3_000_000, 3_000_000]   # two 3s gaps is 20 cpm
        monkeypatch.setattr(check_pulses, "EspPulseDevice", CannedEsp)
        intervals = check_pulses.check(count = 2)
        assert intervals == [3_000_000, 3_000_000]
        assert "rate 20.0 cpm" in capsys.readouterr().out

    def test_sub_dead_time_intervals_trip_the_warning(self, monkeypatch, capsys):
        """One interval under the floor should print the warning with its count"""
        CannedEsp.values = [150, 2_000_000]
        monkeypatch.setattr(check_pulses, "EspPulseDevice", CannedEsp)
        check_pulses.check(count = 2)
        assert "warning: 1 intervals under the 180 us dead time" in capsys.readouterr().out

    def test_clean_run_says_there_were_none(self, monkeypatch, capsys):
        """No intervals under the floor should still print a line saying so"""
        CannedEsp.values = [2_000_000]
        monkeypatch.setattr(check_pulses, "EspPulseDevice", CannedEsp)
        check_pulses.check(count = 1)
        assert "no intervals under the 180 us dead time" in capsys.readouterr().out

    def test_unknown_tube_raises(self, monkeypatch):
        """A tube outside the table has no floor to check against. Currently that is a KeyError."""
        monkeypatch.setattr(check_pulses, "EspPulseDevice", CannedEsp)
        with pytest.raises(KeyError):
            check_pulses.check(count = 1, tube = "not_a_tube")