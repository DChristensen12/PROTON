# Tests everything relating to recording.py

from proton.common import recording
from proton.common.recording import record_samples, record_device
from proton.common.exceptions import ProtonError
from proton.Hardware.Detectors.geiger_counts.readout import RawSample, GeneralCountsDevice

class TestRecordSamples:
    """As it name implies, this tests record samples processes."""

    def test_keeps_data_on_a_proton_error(self, tmp_path):
        """For this, a device that answers with garbage/something not useable raises a ProtonError, so we keep what we
        already have"""
        output = tmp_path / "out.csv"
        calls = {"n": 0}
        def read_one():
            calls["n"] += 1
            if calls["n"] > 2:
                raise ProtonError("garbage")
            return RawSample(calls["n"], 1.0, 0.0, 0.0)
        written = record_samples(read_one = read_one, out_path = output, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert written == 2

    def test_write_header_then_rows(self, tmp_path):
        """the file should open with the column header and then one row per sample, in that order"""
        out = tmp_path / "out.csv"
        read_one = stops_after([RawSample(1, 10.0, 100.0, 1.0), RawSample(2, 11.0, 101.0, 2.0)])
        record_samples(read_one = read_one, out_path = out, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        lines = out.read_text().splitlines()
        assert lines[0] == "pulse_count,tube_rate,wall_time,monotonic"
        assert lines[1] == "1,10.0,100.0,1.0"
        assert lines[2] == "2,11.0,101.0,2.0"

    def test_derives_columns_from_the_sample(self, tmp_path):
        """When no fields given, it should take the column names off the sample itself"""
        out = tmp_path / "out.csv"
        record_samples(read_one = stops_after([RawSample(1, 2.0, 3.0, 4.0)]), out_path = out, duration = 100, poll_interval = 0)
        assert out.read_text().splitlines()[0] == "pulse_count,tube_rate,wall_time,monotonic"

    def test_returns_the_count_written(self, tmp_path):
        """The count that returns SHOULD match how many samples actually landed"""
        out = tmp_path / "out.csv"
        written = record_samples(read_one = stops_after([RawSample(1, 1.0, 1.0, 1.0)] * 3), out_path = out, duration = 100,
                                  poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert written == 3

    def test_keeps_data_when_the_device_drops(self, tmp_path):
        """If the device were to unplug in the middle of a run, it'd show up as an OSError,
        and every row already written must still be saved, so this tests that it does in fact save."""
        out = tmp_path / "out.csv"
        calls = {"n": 0}
        def read_one():
            calls["n"] += 1
            if calls ["n"] > 3:
                raise OSError("unplugged")
            return RawSample(calls["n"], 1.0, 0.0, 0.0)
        written = record_samples(read_one=read_one, out_path = out, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert written == 3
        assert len(out.read_text().splitlines()) == 4 # Should be a header plus three good rows

    def test_keeps_data_on_a_stop(self, tmp_path):
        """stopping the data collection with ctrl c should keep any of the rows already on the disk, and not lose the run"""
        eat = tmp_path / "out.csv"
        scribed = record_samples(read_one= stops_after([RawSample(1, 1.0, 1.0, 1.0)] *4), 
                                 out_path = eat, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert scribed == 4

    def test_creates_the_output_folder(self, tmp_path):
        """This test should make anything missing folders on the path rather than failing to open the file"""
        out = tmp_path / "foo" / "fee" / "out.csv"
        record_samples(read_one = stops_after([RawSample(1, 1.0, 1.0, 1.0)]), out_path = out, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert out.exists()

    def test_stops_at_the_duration(self, tmp_path):
        """IF there were a tiny duration and no sleeping, the loop should end on its own instead of just running forever"""
        berk = tmp_path / "out.csv"
        scribe_of_scribing = record_samples(read_one = lambda: RawSample(1, 1.0, 0.0, 0.0), out_path = berk, duration = 0.02,
                       poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert scribe_of_scribing >= 1

    def test_row_follows_the_header_order(self, tmp_path):
        """The rows are built from the field names, so a reordered header should reorder the values to match as well"""
        out = tmp_path / "out.csv"
        record_samples(read_one = stops_after([RawSample(1, 2.0, 3.0, 4.0)]), out_path = out,
                       duration = 100, poll_interval = 0, fields = ("monotonic", "pulse_count"))
        lines = out.read_text().splitlines()
        assert lines[0] == "monotonic,pulse_count"
        assert lines[1] == "4.0,1"

class TestRecordDevice:
    """This class tests any processes relating to the the device that is doing the recording"""
    def test_records_and_closes_the_device(self, fake_device, tmp_path):
        """This should open the device, record until it drops, return the count, and then close the port."""
        aur = tmp_path / "out.csv"
        written = record_device(fake_device, out_path = aur, fields = GeneralCountsDevice.FIELDS)
        assert written == 3
        assert len(aur.read_text().splitlines()) == 4
        assert fake_device.last.closed is True

    def test_forwards_the_port(self, fake_device, tmp_path, monkeypatch):
        """When a port is handed in, it should reach the device it opens"""
        monkeypatch.setattr(recording, "record_samples", lambda **k: 0)
        record_device(fake_device, out_path = tmp_path / "o.csv", fields = ("a",), port = "/dev/xyz")
        assert fake_device.last.port == "/dev/xyz"
    
    def test_falls_back_to_class_poll_interval(self, fake_device, tmp_path, monkeypatch):
        """With no intervals given, this SHOULD use the device class default rather than just guessing one"""
        captured = {}
        def fake_record_samples(**kwargs):
            captured.update(kwargs)
            return 0
        monkeypatch.setattr(recording, "record_samples", fake_record_samples)
        record_device(fake_device, out_path = tmp_path / "o.csv", fields = ("a",))
        assert captured["poll_interval"] == fake_device.DEFAULT_POLL_INTERVAL

    def test_passes_none_port_through(self, fake_device, tmp_path, monkeypatch):
        """When left unset, the port stays as None, so the device fills in its own default"""
        monkeypatch.setattr(recording, "record_samples", lambda **k: 0)
        record_device(fake_device, out_path = tmp_path / "o.csv", fields = ("a",))
        assert fake_device.last.port is None


    
def stops_after(samples):
    """this builds a read function that hands back the given samples and then stops 
    cleanly with a ctrl c"""
    pulled = iter(samples)
    def read_one():
        try:
            return next(pulled)
        except StopIteration:
            raise KeyboardInterrupt # Clean stop once the canned samples run out
    return read_one

