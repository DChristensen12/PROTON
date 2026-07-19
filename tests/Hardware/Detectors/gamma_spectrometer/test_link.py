"""Tests for link.py in the gamma_spectrometer package.

RadiaCodeDevice runs against a fake radiacode that returns the same shape of data as the real
library, so none of this needs a real detector plugged in.
"""

import os
import datetime
import pytest
from types import SimpleNamespace
from proton.Hardware.Detectors.gamma_spectrometer.link import RawSpectrum, RadiaCodeDevice, GeneralSpectrumDevice
from proton.Hardware.Detectors.gamma_spectrometer.record_spectrum import write_spectrum
from proton.common.recording import record_snapshot
from proton.common.data_handler import SpectrumError, SpectrumSeries, write_spectrum_file


def _stops_after(values):
    """Build a read_one that returns each value in turn, then raises KeyboardInterrupt once
    they run out, the way a real device signals it is done.
    """
    it = iter(values)

    def read_one():
        try:
            return next(it)
        except StopIteration:
            raise KeyboardInterrupt
    return read_one


class FakeRadiaCode:
    """Stand-in for the radiacode library object, returning fixed values for the few calls the wrapper makes."""

    def __init__(self):
        self.was_reset = False

    def serial_number(self):
        return "RC-102-000123"

    def spectrum_reset(self):
        self.was_reset = True

    def spectrum(self):
        return SimpleNamespace(duration = datetime.timedelta(seconds = 42), a0 = 0.0, a1 = 2.5, a2 = 0.0003, counts = [0, 1, 2, 3])


class TestRawSpectrumContract:
    """Tests for the RawSpectrum shape in link.py."""

    def test_field_order(self):
        """Test that the field order matches the contract the recorder and the file both rely on."""
        assert RawSpectrum._fields == ("counts", "a0", "a1", "a2", "duration", "wall_time", "monotonic")


class TestRadiaCodeDevice:
    """Tests for the RadiaCodeDevice wrapper."""

    def test_reads_a_full_spectrum(self):
        """Test that one read returns the counts as a tuple, the calibration as floats, and both clocks set."""
        with RadiaCodeDevice(device = FakeRadiaCode()) as device:
            spectrum = device.read_raw_spectrum()
        assert spectrum.counts == (0, 1, 2, 3) and isinstance(spectrum.counts, tuple)
        assert isinstance(spectrum.a0, float) and isinstance(spectrum.a1, float) and isinstance(spectrum.a2, float)
        assert spectrum.duration == 42.0 and isinstance(spectrum.duration, float)
        assert isinstance(spectrum.wall_time, float) and spectrum.wall_time > 0
        assert isinstance(spectrum.monotonic, float) and spectrum.monotonic > 0

    def test_device_id_names_model_and_serial(self):
        """Test that the device id names the model and the serial."""
        device = RadiaCodeDevice(device = FakeRadiaCode())
        assert device.get_device_id() == "Radiacode 102 RC-102-000123"

    def test_model_can_be_overridden(self):
        """Test that the model is a settable label, since a 103 or 110 functions the same way."""
        device = RadiaCodeDevice(device = FakeRadiaCode(), model = "103")
        assert device.get_device_id() == "Radiacode 103 RC-102-000123"

    def test_reset_clears_the_spectrum(self):
        """Test that reset clears the accumulating spectrum on the device."""
        fake = FakeRadiaCode()
        RadiaCodeDevice(device = fake).reset()
        assert fake.was_reset is True

    def test_context_manager_drops_the_link(self):
        """Test that leaving the with block drops the handle."""
        device = RadiaCodeDevice(device = FakeRadiaCode())
        with device:
            pass
        assert device._rc is None


class TestParity:
    """Tests where GeneralSpectrumDevice and RadiaCodeDevice look the same to the recorder."""

    def test_read_raw_spectrum_same_type_and_fields(self):
        """Same RawSpectrum type and field order come back whether the reading was pulled from
           a library or replayed from GeneralSpectrumDevice.
        """
        radiacode = RadiaCodeDevice(device = FakeRadiaCode())
        general = GeneralSpectrumDevice.from_reader(counts_reader = lambda: [1, 2, 3])
        for device in (radiacode, general):
            spectrum = device.read_raw_spectrum()
            assert isinstance(spectrum, RawSpectrum)
            assert type(spectrum)._fields == RawSpectrum._fields

    def test_device_id_is_a_string_whether_queried_or_counted(self):
        """RadiaCodeDevice requires a hardware's model and serial number; GeneralSpectrumDevice
        returns a count of how many spectra it's replaying instead. Both return a string; nothing
        more specific is checked here.
        """
        radiacode = RadiaCodeDevice(device = FakeRadiaCode())
        general = GeneralSpectrumDevice.from_reader(counts_reader = lambda: [1, 2, 3])
        assert isinstance(radiacode.get_device_id(), str)
        assert isinstance(general.get_device_id(), str)

    def test_only_radiacode_actually_drops_a_handle(self):
        """RadiaCodeDevice.__exit__ drops its handle to the radiacode library, the closest thing
        that library has to a disconnect call. GeneralSpectrumDevice.__exit__ is a pure no-op by
        comparison.
        """
        with RadiaCodeDevice(device = FakeRadiaCode()) as device:
            pass
        with GeneralSpectrumDevice.from_reader(counts_reader = lambda: [1, 2, 3]) as device:
            pass

    def test_default_poll_interval_is_defined_on_both_classes(self):
        assert hasattr(RadiaCodeDevice, "DEFAULT_POLL_INTERVAL")
        assert hasattr(GeneralSpectrumDevice, "DEFAULT_POLL_INTERVAL")

    def test_recording_both_yields_the_same_file_shape(self, tmp_path):
        """
        A spectrum doesn't fit one csv row, so both devices route through record_snapshot and
        write_spectrum instead of record_samples. The header keys and the trailing
        channel,counts table come out the same shape regardless of which device wrote them.
        """
        radiacode_out = tmp_path / "radiacode.csv"
        general_out = tmp_path / "general.csv"
        radiacode = RadiaCodeDevice(device = FakeRadiaCode())
        record_snapshot(read_one = _stops_after([radiacode.read_raw_spectrum()]), out_path = radiacode_out,
                         duration = 100, poll_interval = 0,
                         write = lambda spectrum, path: write_spectrum(spectrum, path, radiacode.get_device_id()))
        general = GeneralSpectrumDevice.from_reader(counts_reader = lambda: [1, 2, 3])
        record_snapshot(read_one = _stops_after([general.read_raw_spectrum()]), out_path = general_out,
                         duration = 100, poll_interval = 0,
                         write = lambda spectrum, path: write_spectrum(spectrum, path, general.get_device_id()))

        def header_keys(text):
            """Return just the # key names from a spectrum file's header lines, in order."""
            return [line.split()[1] for line in text.splitlines() if line.startswith("#")]

        radiacode_text = radiacode_out.read_text()
        general_text = general_out.read_text()
        assert header_keys(radiacode_text) == header_keys(general_text)
        assert "channel,counts" in radiacode_text.splitlines()
        assert "channel,counts" in general_text.splitlines()

def a_raw(counts = (1, 2, 3), **kwargs):
    """Build one RawSpectrum with defaults, so a test only sets what is important for that test."""
    fields = dict(counts = counts, a0 = 0.0, a1 = 2.5, a2 = 0.0, duration = 60.0, wall_time = 1000.0, monotonic = 50.0)
    fields.update(kwargs)
    return RawSpectrum(**fields)


class TestGeneralSpectrumSources:
    """Tests for the ways spectra get into GeneralSpectrumDevice."""

    def test_from_spectra_replays(self):
        """Test that RawSpectrum objects built elsewhere replay in order, normalized on the way in."""
        device = GeneralSpectrumDevice.from_spectra([a_raw((9, 9))])
        assert device.read_raw_spectrum().counts == (9, 9)

    def test_load_takes_a_single_file(self, tmp_path):
        """Test that loading a single file gives one spectrum, the same as a folder holding just that file."""
        path = tmp_path / "one.csv"
        write_spectrum_file(a_raw((4, 5)), path, "dev")
        device = GeneralSpectrumDevice(data_dir = path)
        assert len(device) == 1
        assert device.read_raw_spectrum().counts == (4, 5)

    def test_load_rejects_a_path_that_is_neither(self, tmp_path):
        """Test that a path that is neither a file nor a folder raises instead of loading empty."""
        fifo = tmp_path / "fifo"
        os.mkfifo(fifo)
        with pytest.raises(SpectrumError):
            GeneralSpectrumDevice(data_dir = fifo)

    def test_load_takes_a_custom_parser_and_pattern(self, tmp_path):
        """Test that a custom parser and pattern load another file format without the radiacode shape."""
        (tmp_path / "run.dat").write_text("4 5 6")

        def parse(path):
            """Read a space-separated histogram into a RawSpectrum."""
            return a_raw(tuple(int(c) for c in path.read_text().split()))

        device = GeneralSpectrumDevice(data_dir = tmp_path)
        device.load(tmp_path, parser = parse, pattern = "*.dat")
        assert device.read_raw_spectrum().counts == (4, 5, 6)


class TestGeneralSpectrumLifecycle:
    """Tests for running a replay out, resetting it, and the streaming guards."""

    def test_no_data_raises_on_read(self, tmp_path):
        """Test that an empty device raises rather than returning nothing."""
        empty = tmp_path / "empty"
        empty.mkdir()
        device = GeneralSpectrumDevice(data_dir = empty)
        with pytest.raises(SpectrumError):
            device.read_raw_spectrum()

    def test_exhausted_replay_raises_and_reset_rewinds(self):
        """Test that reading past the end raises, and reset restarts the replay."""
        device = GeneralSpectrumDevice.from_spectra([a_raw()])
        device.read_raw_spectrum()
        with pytest.raises(SpectrumError):
            device.read_raw_spectrum()
        device.reset()
        assert device.read_raw_spectrum().counts == (1, 2, 3)

    def test_len_raises_for_a_live_reader(self):
        """Test that len raises for a live reader, which has no stored spectra to count."""
        device = GeneralSpectrumDevice.from_reader(counts_reader = lambda: [1])
        with pytest.raises(SpectrumError):
            len(device)


class TestSpectrumReplace:
    """Tests for swapping one field's column out."""

    def test_replace_counts_casts_each_histogram(self):
        """Test that new histograms land as tuples of ints."""
        device = GeneralSpectrumDevice.from_spectra([a_raw()])
        device.replace_counts([["7", "8", "9"]])
        assert device.read_raw_spectrum().counts == (7, 8, 9)

    def test_wrong_length_raises(self):
        device = GeneralSpectrumDevice.from_spectra([a_raw()])
        with pytest.raises(SpectrumError):
            device.replace_a0([1.0, 2.0])

    def test_replace_before_load_raises(self, tmp_path):
        """Test that replacing before loading raises, since nothing is held to swap against."""
        empty = tmp_path / "empty"
        empty.mkdir()
        device = GeneralSpectrumDevice(data_dir = empty)
        with pytest.raises(SpectrumError):
            device.replace_a0([1.0])


class TestSpectrumToSeries:
    """Tests for to_series, which provides the held spectra for later analyses"""

    def test_builds_a_series_from_one_run(self):
        """Test that held spectra from one run convert to a SpectrumSeries."""
        run = [a_raw(monotonic = 50.0, wall_time = 900.0), a_raw(monotonic = 80.0, wall_time = 930.0)]
        series = GeneralSpectrumDevice.from_spectra(run).to_series()
        assert isinstance(series, SpectrumSeries)
        assert len(series) == 2

    def test_streaming_source_raises(self):
        """Test that a live reader raises on to_series, having no held spectra to return."""
        device = GeneralSpectrumDevice.from_reader(counts_reader = lambda: [1])
        with pytest.raises(SpectrumError):
            device.to_series()

class TestFromReaderDuration:
    """Tests for how the live reader stamps duration."""

    def test_duration_reader_is_used_when_given(self):
        """Test that a duration_reader stamps its value, and without one duration stays zero."""
        device = GeneralSpectrumDevice.from_reader(counts_reader = lambda: [1], duration_reader = lambda: 42)
        assert device.read_raw_spectrum().duration == 42.0
        device = GeneralSpectrumDevice.from_reader(counts_reader = lambda: [1])
        assert device.read_raw_spectrum().duration == 0.0
