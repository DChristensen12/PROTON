"""Tests for recording.py."""

from proton.common import recording
from proton.common.recording import record_samples, record_device, record_snapshot
from proton.common.exceptions import ProtonError
from proton.Hardware.Detectors.geiger_counts.readout import RawSample, GeneralCountsDevice

class TestRecordSamples:
    """Tests for record_samples."""

    def test_keeps_data_on_a_proton_error(self, tmp_path):
        """Test that a ProtonError from the device keeps the rows already written."""
        output = tmp_path / "out.csv"
        calls = {"n": 0}
        def read_one():
            calls["n"] += 1
            if calls["n"] > 2:
                raise ProtonError("garbage")
            return RawSample(calls["n"], 1.0, 0.0, 0.0)
        written = record_samples(read_one = read_one, out_path = output, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert written == 2

    def test_early_stop_reads_as_a_failure(self, tmp_path, capsys):
        """Test that a ProtonError partway through prints a distinct stderr line naming the
        exception and the row count, and that the rows read before the raise are still on disk.
        """
        output = tmp_path / "out.csv"
        calls = {"n": 0}
        def read_one():
            calls["n"] += 1
            if calls["n"] > 2:
                raise ProtonError("garbage")
            return RawSample(calls["n"], 1.0, 0.0, 0.0)
        written = record_samples(read_one = read_one, out_path = output, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        err = capsys.readouterr().err
        assert written == 2
        assert "stopped early after 2 rows" in err
        assert "garbage" in err
        assert len(output.read_text().splitlines()) == 3  # header plus the two rows read before the raise

    def test_write_header_then_rows(self, tmp_path):
        """Test that the file opens with the column header, then one row per sample, in order."""
        out = tmp_path / "out.csv"
        read_one = stops_after([RawSample(1, 10.0, 100.0, 1.0), RawSample(2, 11.0, 101.0, 2.0)])
        record_samples(read_one = read_one, out_path = out, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        lines = out.read_text().splitlines()
        assert lines[0] == "pulse_count,tube_rate,wall_time,monotonic"
        assert lines[1] == "1,10.0,100.0,1.0"
        assert lines[2] == "2,11.0,101.0,2.0"

    def test_derives_columns_from_the_sample(self, tmp_path):
        """Test that omitting fields derives the column names from the sample itself."""
        out = tmp_path / "out.csv"
        record_samples(read_one = stops_after([RawSample(1, 2.0, 3.0, 4.0)]), out_path = out, duration = 100, poll_interval = 0)
        assert out.read_text().splitlines()[0] == "pulse_count,tube_rate,wall_time,monotonic"

    def test_returns_the_count_written(self, tmp_path):
        """Test that the returned count matches how many samples were written."""
        out = tmp_path / "out.csv"
        written = record_samples(read_one = stops_after([RawSample(1, 1.0, 1.0, 1.0)] * 3), out_path = out, duration = 100,
                                  poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert written == 3

    def test_keeps_data_when_the_device_drops(self, tmp_path):
        """Test that an OSError partway through (the device unplugging) keeps the rows already written."""
        out = tmp_path / "out.csv"
        calls = {"n": 0}
        def read_one():
            calls["n"] += 1
            if calls ["n"] > 3:
                raise OSError("unplugged")
            return RawSample(calls["n"], 1.0, 0.0, 0.0)
        written = record_samples(read_one=read_one, out_path = out, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert written == 3
        assert len(out.read_text().splitlines()) == 4  # header plus three good rows

    def test_keeps_data_on_a_stop(self, tmp_path):
        """Test that a KeyboardInterrupt keeps the rows already written instead of losing the run."""
        eat = tmp_path / "out.csv"
        scribed = record_samples(read_one= stops_after([RawSample(1, 1.0, 1.0, 1.0)] *4),
                                 out_path = eat, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert scribed == 4

    def test_creates_the_output_folder(self, tmp_path):
        """Test that missing folders on the output path are created rather than raising."""
        out = tmp_path / "foo" / "fee" / "out.csv"
        record_samples(read_one = stops_after([RawSample(1, 1.0, 1.0, 1.0)]), out_path = out, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert out.exists()

    def test_stops_at_the_duration(self, tmp_path):
        """Test that a tiny duration ends the loop on its own instead of running forever."""
        berk = tmp_path / "out.csv"
        scribe_of_scribing = record_samples(read_one = lambda: RawSample(1, 1.0, 0.0, 0.0), out_path = berk, duration = 0.02,
                       poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert scribe_of_scribing >= 1

    def test_row_follows_the_header_order(self, tmp_path):
        """Test that a reordered fields tuple reorders the row values to match the header."""
        out = tmp_path / "out.csv"
        record_samples(read_one = stops_after([RawSample(1, 2.0, 3.0, 4.0)]), out_path = out,
                       duration = 100, poll_interval = 0, fields = ("monotonic", "pulse_count"))
        lines = out.read_text().splitlines()
        assert lines[0] == "monotonic,pulse_count"
        assert lines[1] == "4.0,1"

class TestOutcomeReporting:
    """Tests that the line a run prints at the end matches how it ended."""

    def test_full_run_message_is_distinct(self, tmp_path, capsys):
        """Test that a completed run prints its own line, distinct from an early stop."""
        record_samples(read_one = lambda: RawSample(1, 1.0, 0.0, 0.0), out_path = tmp_path / "o.csv",
                       duration = 0.02, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        captured = capsys.readouterr()
        assert "finished the full run" in captured.out
        assert "stopped early" not in captured.err

    def test_zero_rows_says_the_device_returned_nothing(self, tmp_path, capsys):
        """Test that a run gathering nothing states why rather than just reporting a count of zero."""
        record_samples(read_one = lambda: RawSample(1, 1.0, 0.0, 0.0), out_path = tmp_path / "o.csv",
                       duration = 0, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert "the device returned nothing" in capsys.readouterr().err

    def test_snapshot_early_stop_names_the_exception(self, tmp_path, capsys):
        """Test that record_snapshot marks an early stop the same way record_samples does."""
        calls = {"n": 0}
        def read_one():
            calls["n"] += 1
            if calls["n"] > 2:
                raise ProtonError("garbage")
            return calls["n"]
        record_snapshot(read_one = read_one, out_path = tmp_path / "s.txt", duration = 100,
                        poll_interval = 0, write = lambda sample, path: None)
        err = capsys.readouterr().err
        assert "stopped early after 2 snapshots" in err
        assert "garbage" in err

class TestRecordDevice:
    """Tests for record_device."""
    def test_records_and_closes_the_device(self, fake_device, tmp_path):
        """Test that record_device opens the device, records until it drops, returns the count, and closes the port."""
        aur = tmp_path / "out.csv"
        written = record_device(fake_device, out_path = aur, fields = GeneralCountsDevice.FIELDS)
        assert written == 3
        assert len(aur.read_text().splitlines()) == 4
        assert fake_device.last.closed is True

    def test_forwards_the_port(self, fake_device, tmp_path, monkeypatch):
        """Test that a given port reaches the device it opens."""
        monkeypatch.setattr(recording, "record_samples", lambda **k: 0)
        record_device(fake_device, out_path = tmp_path / "o.csv", fields = ("a",), port = "/dev/xyz")
        assert fake_device.last.port == "/dev/xyz"

    def test_falls_back_to_class_poll_interval(self, fake_device, tmp_path, monkeypatch):
        """Test that omitting poll_interval uses the device class default."""
        captured = {}
        def fake_record_samples(**kwargs):
            captured.update(kwargs)
            return 0
        monkeypatch.setattr(recording, "record_samples", fake_record_samples)
        record_device(fake_device, out_path = tmp_path / "o.csv", fields = ("a",))
        assert captured["poll_interval"] == fake_device.DEFAULT_POLL_INTERVAL

    def test_passes_none_port_through(self, fake_device, tmp_path, monkeypatch):
        """Test that an unset port stays None so the device fills in its own default."""
        monkeypatch.setattr(recording, "record_samples", lambda **k: 0)
        record_device(fake_device, out_path = tmp_path / "o.csv", fields = ("a",))
        assert fake_device.last.port is None


class TestRecordSnapshot:
    """Tests for record_snapshot, the counterpart to record_samples for a sample that does not
    fit one csv row, for example a spectrum's whole histogram.
    """

    def test_write_gets_called_once_per_read(self, tmp_path):
        """Test that every read from read_one reaches write with the sample and the same out_path."""
        out = tmp_path / "snap.txt"
        calls = []
        record_snapshot(read_one = stops_after([1, 2, 3]), out_path = out, duration = 100,
                         poll_interval = 0, write = lambda sample, path: calls.append((sample, path)))
        assert calls == [(1, out), (2, out), (3, out)]

    def test_returns_the_count_written(self, tmp_path):
        """Test that the returned count matches how many snapshots were written."""
        written = record_snapshot(read_one = stops_after([1, 2]), out_path = tmp_path / "s.txt",
                                   duration = 100, poll_interval = 0, write = lambda sample, path: None)
        assert written == 2

    def test_keeps_data_on_a_proton_error(self, tmp_path):
        """Test that a ProtonError from the device stops the run cleanly, keeping what already landed."""
        calls = {"n": 0}
        def read_one():
            calls["n"] += 1
            if calls["n"] > 2:
                raise ProtonError("garbage")
            return calls["n"]
        written = record_snapshot(read_one = read_one, out_path = tmp_path / "s.txt", duration = 100,
                                   poll_interval = 0, write = lambda sample, path: None)
        assert written == 2

    def test_keeps_data_when_the_device_drops(self, tmp_path):
        """Test that an OSError partway through stops the run cleanly, the same as record_samples."""
        calls = {"n": 0}
        def read_one():
            calls["n"] += 1
            if calls["n"] > 2:
                raise OSError("unplugged")
            return calls["n"]
        written = record_snapshot(read_one = read_one, out_path = tmp_path / "s.txt", duration = 100,
                                   poll_interval = 0, write = lambda sample, path: None)
        assert written == 2

    def test_stops_at_the_duration(self, tmp_path):
        """Test that a tiny duration ends the loop on its own instead of running forever."""
        written = record_snapshot(read_one = lambda: 1, out_path = tmp_path / "s.txt", duration = 0.02,
                                   poll_interval = 0, write = lambda sample, path: None)
        assert written >= 1

    def test_keeps_data_on_a_stop(self, tmp_path):
        """Test that a KeyboardInterrupt keeps whatever landed before the stop instead of raising."""
        written = record_snapshot(read_one = stops_after([1, 2, 3, 4]), out_path = tmp_path / "s.txt",
                                   duration = 100, poll_interval = 0, write = lambda sample, path: None)
        assert written == 4


def stops_after(samples):
    """Build a read_one that returns the given samples in order, then raises KeyboardInterrupt."""
    pulled = iter(samples)
    def read_one():
        try:
            return next(pulled)
        except StopIteration:
            raise KeyboardInterrupt  # mimics ctrl-c once the canned samples run out
    return read_one
