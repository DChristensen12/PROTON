#Records data for geiger_counts devices. It polls the device over serial and writes each reading into a csv.

import argparse
from pathlib import Path
import proton
from proton.Hardware.Detectors.geiger_counts.readout import RadProDevice, GeneralCountsDevice
from proton.common.recording import record_device

DEFAULT_OUT_NAME = "gc01_background_room.csv" # The run that loads by default when GeneralCountsDevice is built with no hardware
DEFAULT_DATA_DIR = Path(proton.__file__).resolve().parent.parent / "data" / "geiger_counts" # where a fresh recording lands by default, kept in the repo root's data folder, separate from the bundled default_data GeneralCountsDevice reads from

def main():
    "main here reads the run settings off the command line and records one run from the device"
    parser = argparse.ArgumentParser(description = f"record a run from {RadProDevice.__name__}")
    parser.add_argument("--duration", type =float, default = 3600, help = "how long to record, in seconds")
    parser.add_argument("--port", default = RadProDevice.DEFAULT_PORT, help = "serial port the device is on")
    parser.add_argument("--name", default = DEFAULT_OUT_NAME, help = "file name inside the data folder")
    parser.add_argument("--dir", default = str(DEFAULT_DATA_DIR), help = "folder to write into")
    args = parser.parse_args()
    out_path = Path(args.dir) / args.name
    record_device(RadProDevice, out_path = out_path, fields = GeneralCountsDevice.FIELDS, duration = args.duration, port = args.port)

if __name__ == "__main__":
    main()
    