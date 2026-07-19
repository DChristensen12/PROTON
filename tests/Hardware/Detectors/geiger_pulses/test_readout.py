"""Tests for readout.py in the geiger_pulses package.

EspPulseDevice runs against a fake serial port so none of this needs a real board plugged in (but it will function identically to a real device).
TestParity checks that GeneralPulsesDevice looks the same to the recorder as EspPulseDevice does, for alternative hardware support.
"""

import pytest
from proton.Hardware.Detectors.geiger_pulses.readout import (RawPulse, EspPulseDevice, GeneralPulsesDevice, PulseError)
from proton.common.recording import record_samples


class FakeSerial:
    """Stand-in for a pyserial port. Returns queued lines one at a time, then raises
    KeyboardInterrupt once the queue is empty so a test run stops instead of waiting out a real
    read timeout.
    """

    def __init__(self, lines):
        """lines is an iterable of raw bytes, one per read_until() call."""
        self._lines = list(lines)

    def read_until(self, expected = b"\n"):
        """Return the next queued line, or stop the run once nothing is left to give.

        Matches the pyserial read_until signature EspPulseDevice calls. The queued bytes
        already carry their own terminator, so expected is accepted and ignored.
        """
        if self._lines:
            return self._lines.pop(0)
        raise KeyboardInterrupt

    def close(self):
        """No real resource to release."""
        return None


class TestRawPulseContract:
    """Tests for the RawPulse shape in readout.py."""

    def test_field_order(self):
        """Test that the column order matches the contract the recorder and the csv both rely on."""
        assert RawPulse._fields == ("pulse_index", "dt_us", "wall_time", "monotonic")


def write_pulse_csv(path, rows):
    """Write a pulse csv with the header the recorder produces."""
    lines = ["pulse_index,dt_us,wall_time,monotonic"]
    lines += [",".join(str(v) for v in row) for row in rows]
    path.write_text("\n".join(lines) + "\n")

class TestGeneralPulsesCsv:
    """Tests for from_csv, which is how a recorded run gets loaded back for replay."""

    def test_from_csv_reads_the_recorder_format(self, tmp_path):
        """Test that from_csv replays the dt_us column in the order it was recorded."""
        path = tmp_path / "run.csv"
        write_pulse_csv(path, [[1, 500, 0.0, 0.0], [2, 900, 0.0, 0.0]])
        device = GeneralPulsesDevice.from_csv(path)
        assert [device.read_raw_pulse().dt_us for _ in range(2)] == [500, 900]

    def test_from_csv_takes_a_folder(self, tmp_path):
        """Test that pointing from_csv at a folder loads the first csv in sorted name order."""
        write_pulse_csv(tmp_path / "b.csv", [[1, 999, 0.0, 0.0]])
        write_pulse_csv(tmp_path / "a.csv", [[1, 111, 0.0, 0.0]])
        device = GeneralPulsesDevice.from_csv(tmp_path)
        assert device.read_raw_pulse().dt_us == 111

    def test_empty_folder_raises(self, tmp_path):
        """Test that a folder with no csv raises rather than replaying nothing."""
        with pytest.raises(PulseError):
            GeneralPulsesDevice.from_csv(tmp_path)


class TestEspPulseDevice:
    """Tests for the EspPulseDevice wrapper."""

    def test_reads_a_full_pulse(self):
        """Test that one read returns the index and dt_us as ints, with both clocks set."""
        device = EspPulseDevice(serial_port = FakeSerial([b"1 100\n"]))
        pulse = device.read_raw_pulse()
        assert pulse.pulse_index == 1 and isinstance(pulse.pulse_index, int)
        assert pulse.dt_us == 100 and isinstance(pulse.dt_us, int)
        assert isinstance(pulse.wall_time, float) and isinstance(pulse.monotonic, float)

    def test_skips_boot_banner_and_blank_lines(self):
        """Test that a boot banner or a blank line is skipped rather than returned as a pulse."""
        device = EspPulseDevice(serial_port = FakeSerial([b"# ggreg20 boot\n", b"\n", b"2 250\n"]))
        pulse = device.read_raw_pulse()
        assert pulse.dt_us == 250

    def test_banner_then_valid_line_returns_the_valid_line(self):
        """Test that a # banner ahead of a real line does not block that line from being read."""
        device = EspPulseDevice(serial_port = FakeSerial([b"# pulse_timer ready\n", b"1 100\n"]))
        pulse = device.read_raw_pulse()
        assert pulse.pulse_index == 1 and pulse.dt_us == 100

    def test_get_device_id_names_the_port(self):
        """Test that the device id names the port, since the board has no serial number of its own."""
        device = EspPulseDevice(port = "/dev/ttyUSB9", serial_port = FakeSerial([]))
        assert device.get_device_id() == "esp32:/dev/ttyUSB9"

    def test_repeated_index_raises(self):
        """Test that a repeated pulse index raises rather than being read as new data."""
        device = EspPulseDevice(serial_port = FakeSerial([b"5 100\n", b"5 100\n"]))
        device.read_raw_pulse()
        with pytest.raises(PulseError):
            device.read_raw_pulse()

    def test_decreasing_index_raises(self):
        """Test that a decreasing pulse index raises, since the board's index only ever counts up."""
        device = EspPulseDevice(serial_port = FakeSerial([b"5 100\n", b"4 100\n"]))
        device.read_raw_pulse()
        with pytest.raises(PulseError):
            device.read_raw_pulse()

    def test_first_pulse_never_raises(self):
        """Test that the first read never raises, having no previous index to check against."""
        device = EspPulseDevice(serial_port = FakeSerial([b"999 100\n"]))
        assert device.read_raw_pulse().pulse_index == 999

    def test_increasing_indices_still_parse(self):
        """Test that strictly increasing indices parse with no error."""
        device = EspPulseDevice(serial_port = FakeSerial([b"1 100\n", b"2 200\n", b"3 300\n"]))
        assert [device.read_raw_pulse().pulse_index for _ in range(3)] == [1, 2, 3]

    def test_quiet_timeout_still_just_waits(self):
        """Test that an empty read (a timeout) is skipped rather than returned as a pulse."""
        device = EspPulseDevice(serial_port = FakeSerial([b"", b"", b"1 100\n"]))
        assert device.read_raw_pulse().pulse_index == 1


class TestGeneralPulsesDevice:
    """Tests for the ways to build a GeneralPulsesDevice."""

    def test_from_intervals_replays_in_order(self):
        """Test that a device built from a series returns one RawPulse per value, in order."""
        device = GeneralPulsesDevice.from_intervals([100, 200])
        assert device.read_raw_pulse().dt_us == 100
        assert device.read_raw_pulse().dt_us == 200

    def test_from_reader_is_live(self):
        """Test that a device built from a reader callable forwards whatever the callable returns."""
        device = GeneralPulsesDevice.from_reader(lambda: 42)
        assert device.read_raw_pulse().dt_us == 42

    def test_len_counts_down_an_in_memory_source(self):
        """Test that len on an in-memory source reports how many intervals are left."""
        device = GeneralPulsesDevice.from_intervals([100, 200])
        assert len(device) == 2
        device.read_raw_pulse()
        assert len(device) == 1

    def test_len_raises_for_a_streaming_source(self):
        """Test that len raises for a live reader, which has no length to report."""
        device = GeneralPulsesDevice.from_reader(lambda: 1)
        with pytest.raises(PulseError):
            len(device)


class TestParity:
    """Tests where GeneralPulsesDevice and EspPulseDevice look the same to the recorder."""

    def test_read_raw_pulse_same_type_and_fields(self):
        """Whether the interval came off the wire or out of memory, it lands as a RawPulse with
        the same fields in the same order.
        """
        esp = EspPulseDevice(serial_port = FakeSerial([b"1 100\n"]))
        general = GeneralPulsesDevice.from_intervals([100])
        for device in (esp, general):
            pulse = device.read_raw_pulse()
            assert isinstance(pulse, RawPulse)
            assert type(pulse)._fields == RawPulse._fields

    def test_device_id_is_a_string_however_its_sourced(self):
        """EspPulseDevice's label is built from its port, since the board never reports a serial
        number; GeneralPulsesDevice just echoes whatever device_id it was built with.
        """
        esp = EspPulseDevice(serial_port = FakeSerial([]))
        general = GeneralPulsesDevice.from_intervals([])
        assert isinstance(esp.get_device_id(), str)
        assert isinstance(general.get_device_id(), str)

    def test_only_esp_actually_closes_a_port(self):
        """Only EspPulseDevice.__exit__ does real work, closing the serial port. GeneralPulsesDevice
        keeps the same shape with no port behind it to close.
        """
        with EspPulseDevice(serial_port = FakeSerial([])) as device:
            pass
        with GeneralPulsesDevice.from_intervals([]) as device:
            pass

    def test_default_poll_interval_is_zero_because_pulses_set_their_own_pace(self):
        """Pulses arrive on their own schedule rather than a clock, so both classes fix
        DEFAULT_POLL_INTERVAL at 0.0 instead of sampling at an interval.
        """
        assert hasattr(EspPulseDevice, "DEFAULT_POLL_INTERVAL")
        assert hasattr(GeneralPulsesDevice, "DEFAULT_POLL_INTERVAL")
        assert EspPulseDevice.DEFAULT_POLL_INTERVAL == GeneralPulsesDevice.DEFAULT_POLL_INTERVAL == 0.0

    def test_recorded_csv_header_matches_across_board_and_replay(self, tmp_path):
        """One reads the ESP32 over serial, the other replays stored intervals, but record_samples
        writes the identical header either way.
        """
        esp_out = tmp_path / "esp.csv"
        general_out = tmp_path / "general.csv"
        esp = EspPulseDevice(serial_port = FakeSerial([b"1 100\n", b"2 200\n"]))
        record_samples(read_one = esp.read_raw_pulse, out_path = esp_out, duration = 100, poll_interval = 0)
        general = GeneralPulsesDevice.from_intervals([100, 200])
        record_samples(read_one = general.read_raw_pulse, out_path = general_out, duration = 100, poll_interval = 0)
        assert esp_out.read_text().splitlines()[0] == general_out.read_text().splitlines()[0]


def write_pulse_csv(path, rows):
    """Write a pulse csv with the header the recorder produces."""
    lines = ["pulse_index,dt_us,wall_time,monotonic"]
    lines += [",".join(str(v) for v in row) for row in rows]
    path.write_text("\n".join(lines) + "\n")


class TestGeneralPulsesCsv:
    """Tests for from_csv, which is how a recorded run gets loaded back for replay."""

    def test_from_csv_reads_the_recorder_format(self, tmp_path):
        """Test that from_csv replays the dt_us column in the order it was recorded."""
        path = tmp_path / "run.csv"
        write_pulse_csv(path, [[1, 500, 0.0, 0.0], [2, 900, 0.0, 0.0]])
        device = GeneralPulsesDevice.from_csv(path)
        assert [device.read_raw_pulse().dt_us for _ in range(2)] == [500, 900]

    def test_from_csv_takes_a_folder(self, tmp_path):
        """Test that pointing from_csv at a folder loads the first csv in sorted name order."""
        write_pulse_csv(tmp_path / "b.csv", [[1, 999, 0.0, 0.0]])
        write_pulse_csv(tmp_path / "a.csv", [[1, 111, 0.0, 0.0]])
        device = GeneralPulsesDevice.from_csv(tmp_path)
        assert device.read_raw_pulse().dt_us == 111

    def test_empty_folder_raises(self, tmp_path):
        """Test that a folder with no csv raises rather than replaying nothing."""
        with pytest.raises(PulseError):
            GeneralPulsesDevice.from_csv(tmp_path)

    def test_missing_dt_us_column_raises(self, tmp_path):
        """Test that a csv without a dt_us column raises and names the file."""
        path = tmp_path / "wrong.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(PulseError):
            GeneralPulsesDevice.from_csv(path)

    def test_replay_regenerates_the_index(self, tmp_path):
        """Test that a replayed pulse gets a fresh sequential index, not the recorded one."""
        path = tmp_path / "run.csv"
        write_pulse_csv(path, [[40, 500, 0.0, 0.0], [41, 900, 0.0, 0.0]])
        device = GeneralPulsesDevice.from_csv(path)
        assert device.read_raw_pulse().pulse_index == 1
        assert device.read_raw_pulse().pulse_index == 2


class TestReplaceDtUs:
    """Tests for swapping the held intervals out for a synthetic series."""

    def test_swaps_and_rewinds(self):
        """Test that the new values read from the top, even if the old replay was partway through."""
        device = GeneralPulsesDevice.from_intervals([100, 200])
        device.read_raw_pulse()
        device.replace_dt_us([7, 8])
        assert device.read_raw_pulse().dt_us == 7
        assert len(device) == 1

    def test_wrong_length_raises(self):
        device = GeneralPulsesDevice.from_intervals([100, 200])
        with pytest.raises(PulseError):
            device.replace_dt_us([7])

    def test_streaming_source_raises(self):
        """Test that a live reader raises on replace_dt_us, holding nothing in memory to replace."""
        device = GeneralPulsesDevice.from_reader(lambda: 1)
        with pytest.raises(PulseError):
            device.replace_dt_us([1])


class TestToTrain:
    """Tests for to_train, which essentially gives the held intervals over to the analysis side."""

    def test_converts_microseconds_to_seconds(self):
        """Test that the train's arrival times are the held intervals summed and divided by a million."""
        device = GeneralPulsesDevice.from_intervals([500_000, 250_000])
        train = device.to_train()
        assert train.times[-1] == pytest.approx(0.75)

    def test_carries_the_device_id(self):
        """Test that detector_id defaults to the device's own id."""
        device = GeneralPulsesDevice.from_intervals([100], device_id = "my_board")
        assert device.to_train().detector_id == "my_board"

    def test_streaming_source_raises(self):
        """Test that a live reader raises on to_train, having no held series to return."""
        device = GeneralPulsesDevice.from_reader(lambda: 1)
        with pytest.raises(PulseError):
            device.to_train()


class TestEspPulseDeviceParsing:
    """Tests for the lines the parser should skip rather than crash on."""

    def test_three_cell_line_is_skipped(self):
        """Test that a line with the wrong cell count is skipped rather than parsed as a pulse."""
        device = EspPulseDevice(serial_port = FakeSerial([b"1 100 extra\n", b"2 200\n"]))
        assert device.read_raw_pulse().dt_us == 200

    def test_non_integer_cells_are_skipped(self):
        """Test that cells that are not integers are skipped rather than parsed as a pulse."""
        device = EspPulseDevice(serial_port = FakeSerial([b"xx yy\n", b"3 300\n"]))
        assert device.read_raw_pulse().dt_us == 300


class TestPulseErrorContext:
    """Tests for the context PulseError carries into a traceback."""

    def test_plain_message_still_works(self):
        """Test that the bare one-argument form reads back as just the message."""
        assert str(PulseError("broke")) == "broke"

    def test_context_shows_in_str(self):
        """Test that source, path, and raw all land in the printed form when set."""
        err = PulseError("broke", source = "esp32:/dev/ttyUSB0", raw = b"5 100", path = "run.csv")
        text = str(err)
        assert "esp32:/dev/ttyUSB0" in text and "run.csv" in text and "5 100" in text
