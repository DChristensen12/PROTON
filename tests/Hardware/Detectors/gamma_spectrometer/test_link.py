"""Tests for link.py in the gamma_spectrometer package. RadiaCodeDevice runs against a fake radiacode
that answers like the real library, so none of this needs a real detector plugged in to test that it works."""

import datetime
from types import SimpleNamespace
from proton.Hardware.Detectors.gamma_spectrometer.link import RawSpectrum, RadiaCodeDevice


class FakeRadiaCode:
    """This stands in for the radiacode library object, answering the few calls the wrapper makes"""

    def __init__(self):
        self.was_reset = False

    def serial_number(self):
        return "RC-102-000123"

    def spectrum_reset(self):
        self.was_reset = True

    def spectrum(self):
        return SimpleNamespace(duration = datetime.timedelta(seconds = 42), a0 = 0.0, a1 = 2.5, a2 = 0.0003, counts = [0, 1, 2, 3])


class TestRawSpectrumContract:
    """Tests relating to the RawSpectrum shape in link.py"""

    def test_field_order(self):
        """The field order is a contract the recorder and the file both lean on, so it gets pinned"""
        assert RawSpectrum._fields == ("counts", "a0", "a1", "a2", "duration", "wall_time", "monotonic")


class TestRadiaCodeDevice:
    """Tests relating to the RadiaCodeDevice wrapper"""

    def test_reads_a_full_spectrum(self):
        """One read should give the counts as a tuple, the calibration as floats, and both clocks set"""
        with RadiaCodeDevice(device = FakeRadiaCode()) as device:
            spectrum = device.read_raw_spectrum()
        assert spectrum.counts == (0, 1, 2, 3) and isinstance(spectrum.counts, tuple)
        assert isinstance(spectrum.a0, float) and isinstance(spectrum.a1, float) and isinstance(spectrum.a2, float)
        assert spectrum.duration == 42.0 and isinstance(spectrum.duration, float)
        assert isinstance(spectrum.wall_time, float) and spectrum.wall_time > 0
        assert isinstance(spectrum.monotonic, float) and spectrum.monotonic > 0

    def test_device_id_names_model_and_serial(self):
        """The id should name the model and the serial, so a run records which detector made it"""
        device = RadiaCodeDevice(device = FakeRadiaCode())
        assert device.get_device_id() == "Radiacode 102 RC-102-000123"

    def test_model_can_be_overridden(self):
        """A 103 or 110 talks the same way, so the model is just a label you can set"""
        device = RadiaCodeDevice(device = FakeRadiaCode(), model = "103")
        assert device.get_device_id() == "Radiacode 103 RC-102-000123"

    def test_reset_clears_the_spectrum(self):
        """reset should reach through and clear the accumulating spectrum on the device"""
        fake = FakeRadiaCode()
        RadiaCodeDevice(device = fake).reset()
        assert fake.was_reset is True

    def test_context_manager_drops_the_link(self):
        """Leaving the with block should drop the handle so the connection can be let go"""
        device = RadiaCodeDevice(device = FakeRadiaCode())
        with device:
            pass
        assert device._rc is None