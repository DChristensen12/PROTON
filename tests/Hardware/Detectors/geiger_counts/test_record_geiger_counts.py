# Tests for the counts recorder script. record_device is patched out, so this only checks that the command line flags reach it (with no hardware and no serial port).

import sys
from proton.Hardware.Detectors.geiger_counts import record_geiger_counts
from proton.Hardware.Detectors.geiger_counts.readout import RadProDevice, GeneralCountsDevice

class TestMain:
    """Tests that main wires the command line flags into record_device"""

    def test_flags_reach_record_device(self, tmp_path, monkeypatch):
        """duration, port, and the output path should all land where record_device expects them"""
        captured = {}
        monkeypatch.setattr(record_geiger_counts, "record_device",
                            lambda device_cls, **kw: captured.update(kw, device_cls = device_cls) or 0)
        monkeypatch.setattr(sys, "argv", ["prog", "--duration", "5", "--port", "/dev/xyz",
                                          "--name", "run.csv", "--dir", str(tmp_path)])
        record_geiger_counts.main()
        assert captured["device_cls"] is RadProDevice
        assert captured["duration"] == 5
        assert captured["port"] == "/dev/xyz"
        assert captured["out_path"] == tmp_path / "run.csv"
        assert captured["fields"] == GeneralCountsDevice.FIELDS
