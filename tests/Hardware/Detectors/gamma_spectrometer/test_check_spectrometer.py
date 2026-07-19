""" Tests for check_spectrometer, run against a fake device with wait set to zero. """

from proton.Hardware.Detectors.gamma_spectrometer import check_spectrometer
from proton.Hardware.Detectors.gamma_spectrometer.link import RadiaCodeDevice
from .test_link import FakeRadiaCode

def fake_device(bluetooth_mac = None):
    """Build a RadiaCodeDevice around the fake one, matching the call check() makes."""
    return RadiaCodeDevice(device = FakeRadiaCode())

class TestCheck:
    """Tests that check reads twice and reports what it was given."""

    def test_prints_id_channels_and_counts(self, monkeypatch, capsys):
        """Test that one run prints the device id, the channel count, and both count readings."""
        monkeypatch.setattr(check_spectrometer, "RadiaCodeDevice", fake_device)
        check_spectrometer.check(wait = 0)
        out = capsys.readouterr().out
        assert "connected to Radiacode 102" in out
        assert "channels: 4" in out
        assert "counts right after reset:" in out
