#Records data for geiger_counts devices. It polls the device over serial and writes each reading into a csv.

import argparse
from proton.Hardware.Detectors.geiger_counts.readout import RadProDevice, GeneralCountsDevice
from proton.common.recording import record_device

DEFAULT_OUT_NAME = "gc01_background_room.csv" # The run that loads by default when GeneralCountsDevice is built with no hardware

def main():
    "main here reads the run settings off the command line and records one run from the device"
    parser = argparse.ArgumentParser(description = f"record a run from {RadProDevice.__name__}")
    parser.add_argument("--duration", type =float, default = 3600, help = "how long to record, in seconds")
    parser.add_argument("--port", default = RadProDevice.DEFAULT_PORT, help = "serial port teh device is on")
    parser.add_argument("--name", default = DEFAULT_OUT_NAME, help = "file name inside the data folder")
    args = parser.parse_args()
    out_path = GeneralCountsDevice.DEFAULT_DATA_DIR / args.name
    record_device(RadProDevice, out_path = out_path, fields = GeneralCountsDevice.FIELDS, duration = args.duration, port = args.port)

if __name__ == "__main__":
    main()
    

