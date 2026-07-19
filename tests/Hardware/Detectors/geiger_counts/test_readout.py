"""Tests for readout.py, run against a fake serial port and small temp csvs (to ensure the software works as intended without having to hook it up to a device)"""

import pytest
from proton.Hardware.Detectors.geiger_counts.readout import (
    RawSample,
    GeneralCountsDevice,
    RadProDevice,
    RadProError,
)
from proton.common.recording import record_samples


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


class TestRawSampleContract:
    """Tests for the RawSample contract in readout.py."""

    def test_field_order(self):
        """Test that the column order matches the contract the recorder and the csv both rely on."""
        assert RawSample._fields == ("pulse_count", "tube_rate", "wall_time", "monotonic")

    def test_fields_match_the_device(self):
        """Test that GeneralCountsDevice.FIELDS matches RawSample._fields."""
        assert GeneralCountsDevice.FIELDS == RawSample._fields


class TestRadProDevice:
    """Tests for the RadProDevice class."""

    def test_reads_a_full_sample(self, fake_serial, real_replies):
        """Test that a read returns the count as an int, the rate as a float, and both clocks set."""
        with RadProDevice(serial_port = fake_serial(real_replies)) as dev:
            sample = dev.read_raw_sample()
        assert sample.pulse_count == 26928 and isinstance(sample.pulse_count, int)
        assert sample.tube_rate == 19.152 and isinstance(sample.tube_rate, float)
        assert isinstance(sample.wall_time, float) and isinstance(sample.monotonic, float)

    def test_error_reply_raises(self, fake_serial):
        """Test that an ERROR reply from the device raises RadProError instead of returning a bad value."""
        dev = RadProDevice(serial_port = fake_serial({"GET tubePulseCount": [b"ERROR\r\n"]}))
        with pytest.raises(RadProError):
            dev.get_pulse_count()


class TestGeneralCountsReplay:
    """Tests for GeneralCountsDevice replaying data it loaded."""

    def test_replays_loaded_rows(self, sample_csv):
        """Test that loading a csv replays the rows in order with the right types."""
        dev = GeneralCountsDevice(data_dir = sample_csv)
        assert len(dev) == 2
        first = dev.read_raw_sample()
        assert first.pulse_count == 10 and isinstance(first.pulse_count, int)
        assert dev.read_raw_sample().pulse_count == 11


class TestGeneralCountsReaders:
    """Tests for GeneralCountsDevice built from custom read functions."""

    def test_from_readers_casts_and_stamps(self):
        """Test that from_readers casts the count and rate to the right types and stamps both clocks."""
        dev = GeneralCountsDevice.from_readers(read_pulse_count = lambda: "42", read_tube_rate = lambda: 7)
        sample = dev.read_raw_sample()
        assert sample.pulse_count == 42 and isinstance(sample.pulse_count, int)
        assert sample.tube_rate == 7.0 and isinstance(sample.tube_rate, float)
        assert sample.wall_time > 0 and sample.monotonic > 0


class TestParity:
    """Tests where GeneralCountsDevice and RadProDevice are essentially the same to the recorder."""

    def test_both_share_the_sample_contract(self, fake_serial, real_replies, sample_csv):
        """A serial poll and a replayed csv row both land as a RawSample with the same field
        types: int, float, float, float.
        """
        radpro = RadProDevice(serial_port = fake_serial(real_replies))
        general = GeneralCountsDevice(data_dir = sample_csv)
        for device in (radpro, general):
            sample = device.read_raw_sample()
            assert isinstance(sample, RawSample)
            assert isinstance(sample.pulse_count, int)
            assert isinstance(sample.tube_rate, float)
            assert isinstance(sample.wall_time, float)
            assert isinstance(sample.monotonic, float)

    def test_device_id_is_a_string_whether_read_or_made_up(self, fake_serial, real_replies, sample_csv):
        """RadProDevice reads its id off the wire; GeneralCountsDevice invents one from how
        many rows it loaded. Either way the recorder just needs a string back.
        """
        radpro = RadProDevice(serial_port = fake_serial(real_replies))
        general = GeneralCountsDevice(data_dir = sample_csv)
        assert isinstance(radpro.get_device_id(), str)
        assert isinstance(general.get_device_id(), str)

    def test_only_radpro_actually_closes_a_port(self, fake_serial, real_replies, sample_csv):
        """RadProDevice.__exit__ closes the real serial port on the way out; GeneralCountsDevice
        has nothing to release. Both still have to work inside a with block.
        """
        with RadProDevice(serial_port = fake_serial(real_replies)) as device:
            pass
        with GeneralCountsDevice(data_dir = sample_csv) as device:
            pass

    def test_default_poll_interval_is_defined_on_both_classes(self):
        assert hasattr(RadProDevice, "DEFAULT_POLL_INTERVAL")
        assert hasattr(GeneralCountsDevice, "DEFAULT_POLL_INTERVAL")

    def test_recorded_csv_header_matches_across_wire_and_replay(self, tmp_path, fake_serial, real_replies, sample_csv):
        """RadProDevice polls real hardware; GeneralCountsDevice replays a csv. record_samples
        gives both the same pulse_count,tube_rate,wall_time,monotonic header regardless.
        """
        radpro_out = tmp_path / "radpro.csv"
        general_out = tmp_path / "general.csv"
        radpro = RadProDevice(serial_port = fake_serial(real_replies))
        record_samples(read_one = _stops_after([radpro.read_raw_sample()]), out_path = radpro_out,
                        duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        general = GeneralCountsDevice(data_dir = sample_csv)
        record_samples(read_one = _stops_after([general.read_raw_sample(), general.read_raw_sample()]),
                        out_path = general_out, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert radpro_out.read_text().splitlines()[0] == general_out.read_text().splitlines()[0]

class TestGeneralCountsFromSamples:
    """Tests for from_samples, which takes RawSample objects already in memory."""

    def test_replays_in_order_with_casts(self):
        """Test that samples built elsewhere replay in order, cast to the types RadProDevice produces."""
        device = GeneralCountsDevice.from_samples([RawSample("5", "1.5", 0.0, 0.0)])
        sample = device.read_raw_sample()
        assert sample.pulse_count == 5 and isinstance(sample.pulse_count, int)
        assert sample.tube_rate == 1.5 and isinstance(sample.tube_rate, float)

    def test_carries_the_device_id(self):
        """Test that a named device answers get_device_id with that name."""
        device = GeneralCountsDevice.from_samples([RawSample(1, 1.0, 0.0, 0.0)], device_id = "mine")
        assert device.get_device_id() == "mine"


class TestGeneralCountsReplayLifecycle:
    """Tests for running a replay out, resetting it, and swapping datasets."""

    def test_exhausted_replay_raises_and_reset_rewinds(self, sample_csv):
        """Test that reading past the end raises, and reset restarts the replay."""
        device = GeneralCountsDevice(data_dir = sample_csv)
        device.read_raw_sample()
        device.read_raw_sample()
        with pytest.raises(ValueError):
            device.read_raw_sample()
        device.reset()
        assert device.read_raw_sample().pulse_count == 10

    def test_load_swaps_rather_than_stacks(self, sample_csv, tmp_path):
        """Test that loading a second folder replaces the rows instead of appending to them."""
        other = tmp_path / "other"
        other.mkdir()
        (other / "run.csv").write_text(
            "pulse_count,tube_rate,wall_time,monotonic\n99,1.0,0.0,0.0\n"
        )
        device = GeneralCountsDevice(data_dir = sample_csv)
        device.load(other)
        assert len(device) == 1
        assert device.read_raw_sample().pulse_count == 99

    def test_missing_columns_name_the_file(self, tmp_path):
        """Test that a csv missing the four fields raises with the file's name in the message."""
        bad = tmp_path / "bad.csv"
        bad.write_text("a,b\n1,2\n")
        with pytest.raises(ValueError) as err:
            GeneralCountsDevice(data_dir = tmp_path)
        assert "bad.csv" in str(err.value)

    def test_len_raises_for_a_live_reader(self):
        """Test that len raises for a live reader, which has no stored rows to count."""
        device = GeneralCountsDevice.from_readers(read_pulse_count = lambda: 1, read_tube_rate = lambda: 1.0)
        with pytest.raises(ValueError):
            len(device)


class TestReplaceColumns:
    """Tests for swapping one field's column out."""

    def test_replace_pulse_count_swaps_and_casts(self, sample_csv):
        """Test that the new column lands cast to int, with the other fields untouched."""
        device = GeneralCountsDevice(data_dir = sample_csv)
        device.replace_pulse_count(["7", "8"])
        sample = device.read_raw_sample()
        assert sample.pulse_count == 7 and sample.tube_rate == 20.0

    def test_wrong_length_raises(self, sample_csv):
        device = GeneralCountsDevice(data_dir = sample_csv)
        with pytest.raises(ValueError):
            device.replace_pulse_count([1])

    def test_replace_before_load_raises(self, tmp_path):
        """Test that replacing before loading raises, since nothing is held to swap against."""
        empty = tmp_path / "empty"
        empty.mkdir()
        device = GeneralCountsDevice(data_dir = empty)
        with pytest.raises(ValueError):
            device.replace_pulse_count([1])


class TestToSeries:
    """Tests for to_series, which gives the held samples for later data analysis."""

    def test_differences_the_cumulative_count(self, sample_csv):
        """Test that pulse_count, a running total, differences into counts per interval."""
        device = GeneralCountsDevice(data_dir = sample_csv)
        assert list(device.to_series().counts) == [1]  # 10 to 11 is one count

    def test_t0_comes_off_the_first_wall_time(self, sample_csv):
        """Test that t0 anchors at the first sample's wall_time."""
        device = GeneralCountsDevice(data_dir = sample_csv)
        assert device.to_series().t0 == 1000.0

    def test_streaming_source_raises(self):
        """Test that a live reader raises on to_series, having no held rows to hand over."""
        device = GeneralCountsDevice.from_readers(read_pulse_count = lambda: 1, read_tube_rate = lambda: 1.0)
        with pytest.raises(ValueError):
            device.to_series()
