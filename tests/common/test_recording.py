# Tests everything relating to recording.py

import pytest
from proton.common import recording
from proton.common.recording import record_samples, record_device
from proton.common.exceptions import ProtonError
from proton.Hardware.Detectors.geiger_counts.readout import RawSample, GeneralCountsDevice

class TestRecordSamples:
    """As it name implies, this tests record samples."""
    def test_write_header_then_rows(self, tmp_path):
        """the file should open with the column header and then on row per sample, in that order"""
        out = tmp_path / "out.csv"
        read_one = stops_after([RawSample(1, 10.0, 100.0, 1.0), RawSample(2, 11.0, 101.0, 2.0)])
        record_samples(read_one = read_one, out_path = out, duration = 100, poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        lines = out.read_text().splitlines()
        assert lines[0] == "pulse_count,tube_rate,wall_time,monotonic"
        assert lines[1] == "1,10.0,100.0,1.0"
        assert lines[2] == "2,11.0,101.0,2.0"

    def test_derives_columns_from_the_sample(self, tmp__path):
        """When no fields given, it should take the column names off the sample itself"""
        out = tmp__path / "out.csv"
        record_samples(read_one = stops_after([RawSample(1, 2.0, 3.0, 4.0)]), out_path = out, duration = 100, poll_interval = 0)
        assert out.read_text().splitlines()[0] == "pulse_count,tube_rate,wall_time,monotonic"

    def test_returns_the_count_written(self, tmp__path):
        """The count that returns SHOULD match how many samples actually landed"""
        out = tmp__path / "out.csv"
        written = record_samples(read_one = stops_after([RawSample(1, 1.0, 1.0, 1.0)] * 3), out_path = out, duration = 100,
                                  poll_interval = 0, fields = GeneralCountsDevice.FIELDS)
        assert written == 3
    

def stops_after(samples):
    """this builds a read functioin that hands back the given samples and then stops 
    cleanly with a ctrl c"""
    pulled = iter(samples)
    def read_one():
        try:
            return next(pulled)
        except StopIteration:
            raise KeyboardInterrupt # Clean stop once the canned samples run out
    return read_one



### NOT FINISHED### 