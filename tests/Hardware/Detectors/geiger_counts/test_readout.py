# This has all the tests for readout.py, which are ran against a fake serial port and small temp csvs so no real GC-01 is needed for these tests :)

import pytest
from proton.Hardware.Detectors.geiger_counts.readout import (
    RawSample,
    GeneralCountsDevice,
    RadProDevice,
    RadProError,
)

class TestRawSampleContract:
    """All tests relating to the RawSample contract in readout.py"""

    def test_field_order(self):
        """The column order is a contract the recorder and the csv both rely on, so it gets pinned 0-0"""
        assert RawSample._fields == ("pulse_count", "tube_rate", "wall_time", "monotonic")

    def test_fields_match_the_device(self):
        """GeneralCountsDevice writes and reads by these names, so they have to match the sample"""
        assert GeneralCountsDevice.FIELDS == RawSample._fields


class TestRadProDevice:
    """Has all the tests relating to the RadProDevice class"""

    def test_reads_a_full_sample(self, fake_serial, real_replies):
        """This read should give the count as an int, the rate as a float, and both clocks set"""
        with RadProDevice(serial_port = fake_serial(real_replies)) as dev:
            sample = dev.read_raw_sample()
        assert sample.pulse_count == 26928 and isinstance(sample.pulse_count, int)
        assert sample.tube_rate == 19.152 and isinstance(sample.tube_rate, float)
        assert isinstance(sample.wall_time, float) and isinstance(sample.monotonic, float)

    def test_error_reply_raises(self, fake_serial):
        """An ERROR back from the device should surface as our own error, not a bad value that isn't reported"""
        dev = RadProDevice(serial_port = fake_serial({"GET tubePulseCount": [b"ERROR\r\n"]}))
        with pytest.raises(RadProError):
            dev.get_pulse_count()


class TestGeneralCountsReplay:
    """This has all tests for GeneralCountsDevice replaying data it loaded"""

    def test_replays_loaded_rows(self, sample_csv):
        """This should load the csv and hand the rows back in order with the right types"""
        dev = GeneralCountsDevice(data_dir = sample_csv)
        assert len(dev) == 2
        first = dev.read_raw_sample()
        assert first.pulse_count == 10 and isinstance(first.pulse_count, int)
        assert dev.read_raw_sample().pulse_count == 11


class TestGeneralCountsReaders:
    """All tests for GeneralCountsDevice built from your own read functions"""

    def test_from_readers_casts_and_stamps(self):
        """This function should cast the count and rate to the right types and stamp both clocks itself"""
        dev = GeneralCountsDevice.from_readers(read_pulse_count = lambda: "42", read_tube_rate = lambda: 7)
        sample = dev.read_raw_sample()
        assert sample.pulse_count == 42 and isinstance(sample.pulse_count, int)
        assert sample.tube_rate == 7.0 and isinstance(sample.tube_rate, float)
        assert sample.wall_time > 0 and sample.monotonic > 0


class TestParity:
    """This is all tests where GeneralCountsDevice and RadProDevice look the same to the recorder"""

    def test_both_share_the_sample_contract(self, fake_serial, real_replies, sample_csv):
        """the recorder cannot tell them apart, so both must hand back a RawSample with the same types"""
        radpro = RadProDevice(serial_port = fake_serial(real_replies))
        general = GeneralCountsDevice(data_dir = sample_csv)
        for device in (radpro, general):
            sample = device.read_raw_sample()
            assert isinstance(sample, RawSample)
            assert isinstance(sample.pulse_count, int)
            assert isinstance(sample.tube_rate, float)
            assert isinstance(sample.wall_time, float)
            assert isinstance(sample.monotonic, float)
