# Tests for the spectrum recorder. write_spectrum is the piece with real logic worth pinning, since the
# file it makes is what a later reader will replay, so we build a spectrum and check the file it writes.

from proton.Hardware.Detectors.gamma_spectrometer.link import RawSpectrum
from proton.Hardware.Detectors.gamma_spectrometer.record_spectrum import write_spectrum


def a_spectrum():
    """builds one small RawSpectrum to write out"""
    return RawSpectrum(counts = (5, 6, 7), a0 = 0.0, a1 = 2.5, a2 = 0.0003, duration = 60.0, wall_time = 1000.0, monotonic = 12.0)


class TestWriteSpectrum:
    """Tests relating to writing a spectrum out to a file"""

    def test_writes_header_and_table(self, tmp_path):
        """The file should open with the metadata header, then a channel and counts table that reads back right"""
        out = tmp_path / "s.csv"
        write_spectrum(a_spectrum(), out, "Radiacode 102 RC-102-000123")
        lines = out.read_text().splitlines()
        assert "# device Radiacode 102 RC-102-000123" in lines
        assert "# duration 60.0" in lines
        assert "# a1 2.5" in lines
        table = lines.index("channel,counts")
        assert lines[table + 1] == "0,5"
        assert lines[table + 2] == "1,6"
        assert lines[table + 3] == "2,7"

    def test_leaves_no_temp_file_behind(self, tmp_path):
        """The temp file it writes into should be swapped in and gone, leaving just the real file"""
        out = tmp_path / "s.csv"
        write_spectrum(a_spectrum(), out, "dev")
        assert out.exists()
        assert not (tmp_path / "s.csv.tmp").exists()