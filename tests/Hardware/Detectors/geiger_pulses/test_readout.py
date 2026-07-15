"""This file has the tests for readout.py in the geiger_pulses package. EspPulseDevice runs against a fake serial
   port so that none of this needs a real board plugged in, and TestParity checks that GeneralPulsesDevice
   looks the same to the recorder as EspPulseDevice does (for similar, but alternative types of hardware support)"""

import pytest
from proton.Hardware.Detectors.geiger_pulses.readout import (RawPulse, EspPulseDevice, GeneralPulsesDevice, PulseError)
from proton.common.recording import record_samples


class FakeSerial:
    """This is a stand in for a pyserial port. It will hand back queued lines one at a time, and then raise
    KeyboardInterrupt once the queue is empty so that a test run stops instead of taking forever like a
    real read timeout would."""

    def __init__(self, lines):
        """lines is an iterable of raw bytes, one per read_until() call"""
        self._lines = list(lines)

    def read_until(self, expected = b"\n"):
        """Returns the next queued line, or stops the run once there is nothing left to give.

        Matches the pyserial read_until signature EspPulseDevice now calls. The queued bytes
        already have their own terminator, so expected is accepted and ignored.
        """
        if self._lines:
            return self._lines.pop(0)
        raise KeyboardInterrupt

    def close(self):
        """Nothing real to release"""
        return None


class TestRawPulseContract:
    """For tests relating to the RawPulse shape in readout.py"""

    def test_field_order(self):
        """The column order is a contract the recorder and the csv both rely on, so it gets pinned"""
        assert RawPulse._fields == ("pulse_index", "dt_us", "wall_time", "monotonic")


class TestEspPulseDevice:
    """For tests relating to the EspPulseDevice wrapper"""

    def test_reads_a_full_pulse(self):
        """One read should give the index and dt_us as ints, and both clocks set"""
        device = EspPulseDevice(serial_port = FakeSerial([b"1 100\n"]))
        pulse = device.read_raw_pulse()
        assert pulse.pulse_index == 1 and isinstance(pulse.pulse_index, int)
        assert pulse.dt_us == 100 and isinstance(pulse.dt_us, int)
        assert isinstance(pulse.wall_time, float) and isinstance(pulse.monotonic, float)

    def test_skips_boot_banner_and_blank_lines(self):
        """A boot banner or a random blank line should not come back as a pulse"""
        device = EspPulseDevice(serial_port = FakeSerial([b"# ggreg20 boot\n", b"\n", b"2 250\n"]))
        pulse = device.read_raw_pulse()
        assert pulse.dt_us == 250

    def test_banner_then_valid_line_returns_the_valid_line(self):
        """A single '#' banner ahead of a real line should not stop that line from coming back"""
        device = EspPulseDevice(serial_port = FakeSerial([b"# pulse_timer ready\n", b"1 100\n"]))
        pulse = device.read_raw_pulse()
        assert pulse.pulse_index == 1 and pulse.dt_us == 100

    def test_get_device_id_names_the_port(self):
        """The id should name the port, since the board has no serial number of its own to report"""
        device = EspPulseDevice(port = "/dev/ttyUSB9", serial_port = FakeSerial([]))
        assert device.get_device_id() == "esp32:/dev/ttyUSB9"

    def test_repeated_index_raises(self):
        """A stale read reprints the same line, and that must raise rather than come back as data"""
        device = EspPulseDevice(serial_port = FakeSerial([b"5 100\n", b"5 100\n"]))
        device.read_raw_pulse()
        with pytest.raises(PulseError):
            device.read_raw_pulse()

    def test_decreasing_index_raises(self):
        """The board's index only ever counts up, so a drop back is impossible and must raise"""
        device = EspPulseDevice(serial_port = FakeSerial([b"5 100\n", b"4 100\n"]))
        device.read_raw_pulse()
        with pytest.raises(PulseError):
            device.read_raw_pulse()

    def test_first_pulse_never_raises(self):
        """There is no previous index to check the first read against, whatever it is"""
        device = EspPulseDevice(serial_port = FakeSerial([b"999 100\n"]))
        assert device.read_raw_pulse().pulse_index == 999

    def test_increasing_indices_still_parse(self):
        """Normal, strictly increasing indices should read through with no error"""
        device = EspPulseDevice(serial_port = FakeSerial([b"1 100\n", b"2 200\n", b"3 300\n"]))
        assert [device.read_raw_pulse().pulse_index for _ in range(3)] == [1, 2, 3]

    def test_quiet_timeout_still_just_waits(self):
        """An empty read is a timeout with nothing arrived yet, not a pulse, so it should be skipped"""
        device = EspPulseDevice(serial_port = FakeSerial([b"", b"", b"1 100\n"]))
        assert device.read_raw_pulse().pulse_index == 1


class TestGeneralPulsesDevice:
    """the tests relating to GeneralPulsesDevice's ways in"""

    def test_from_intervals_replays_in_order(self):
        """Built from a series, it should hand back one RawPulse per value in order"""
        device = GeneralPulsesDevice.from_intervals([100, 200])
        assert device.read_raw_pulse().dt_us == 100
        assert device.read_raw_pulse().dt_us == 200

    def test_from_reader_is_live(self):
        """Built from a reader callable, it should just forward whatever the callable returns"""
        device = GeneralPulsesDevice.from_reader(lambda: 42)
        assert device.read_raw_pulse().dt_us == 42

    def test_len_counts_down_an_in_memory_source(self):
        """A source built from a series in memory should report how many intervals are left"""
        device = GeneralPulsesDevice.from_intervals([100, 200])
        assert len(device) == 2
        device.read_raw_pulse()
        assert len(device) == 1

    def test_len_raises_for_a_streaming_source(self):
        """A live reader has no length to report, so it must report that it doesn't"""
        device = GeneralPulsesDevice.from_reader(lambda: 1)
        with pytest.raises(PulseError):
            len(device)


class TestParity:
    """Tests where GeneralPulsesDevice and EspPulseDevice use the same kind of recorder"""

    def test_read_raw_pulse_same_type_and_fields(self):
        """The recorder distinguish between the two, so both must hand back a RawPulse with the same fields"""
        esp = EspPulseDevice(serial_port = FakeSerial([b"1 100\n"]))
        general = GeneralPulsesDevice.from_intervals([100])
        for device in (esp, general):
            pulse = device.read_raw_pulse()
            assert isinstance(pulse, RawPulse)
            assert type(pulse)._fields == RawPulse._fields

    def test_get_device_id_returns_a_string(self):
        """Both should be able to name themselves for the recorder's log line"""
        esp = EspPulseDevice(serial_port = FakeSerial([]))
        general = GeneralPulsesDevice.from_intervals([])
        assert isinstance(esp.get_device_id(), str)
        assert isinstance(general.get_device_id(), str)

    def test_both_work_as_context_managers(self):
        """Both should be usable in a with block"""
        with EspPulseDevice(serial_port = FakeSerial([])) as device:
            pass
        with GeneralPulsesDevice.from_intervals([]) as device:
            pass

    def test_both_expose_default_poll_interval(self):
        """The recorder reads this off the class to know how it should pace itself"""
        assert hasattr(EspPulseDevice, "DEFAULT_POLL_INTERVAL")
        assert hasattr(GeneralPulsesDevice, "DEFAULT_POLL_INTERVAL")
        assert EspPulseDevice.DEFAULT_POLL_INTERVAL == GeneralPulsesDevice.DEFAULT_POLL_INTERVAL == 0.0

    def test_recording_both_yields_identical_csv_headers(self, tmp_path):
        """A run recorded off either one should produce the same header, in the same column order"""
        esp_out = tmp_path / "esp.csv"
        general_out = tmp_path / "general.csv"
        esp = EspPulseDevice(serial_port = FakeSerial([b"1 100\n", b"2 200\n"]))
        record_samples(read_one = esp.read_raw_pulse, out_path = esp_out, duration = 100, poll_interval = 0)
        general = GeneralPulsesDevice.from_intervals([100, 200])
        record_samples(read_one = general.read_raw_pulse, out_path = general_out, duration = 100, poll_interval = 0)
        assert esp_out.read_text().splitlines()[0] == general_out.read_text().splitlines()[0]
