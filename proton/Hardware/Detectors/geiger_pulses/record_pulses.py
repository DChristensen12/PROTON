"""record_pulses.py records per pulse intervals from the ESP32 to a csv.

It hands read_raw_pulse to the shared recorder with a poll interval of zero, so the recorder never
sleeps and the pulses themselves pace the loop. Every row is flushed as it lands, so pulling the
cable partway through still leaves every interval gathered up to that point.
"""

import argparse
from pathlib import Path

import proton
from proton.common.recording import record_samples
from proton.Hardware.Detectors.geiger_pulses.readout import EspPulseDevice

DEFAULT_NAME = "pulses"
DEFAULT_DIR = Path(proton.__file__).resolve().parent.parent / "data" / "geiger_pulses" # the repo root's data folder, so this lands in the same place regardless of the cwd it's run from


def record(name = DEFAULT_NAME, out_dir = DEFAULT_DIR, duration = 3600, port = None):
    """Open the device and record a run to out_dir/name.csv"""
    out_path = Path(out_dir) / (name + ".csv")
    with EspPulseDevice(port = port) as device:
        print("recording from", device.get_device_id())
        return record_samples(
            read_one = device.read_raw_pulse,
            out_path = out_path,
            duration = duration,
            poll_interval = EspPulseDevice.DEFAULT_POLL_INTERVAL,
        )


def main():
    """Parse the command line and start a run"""
    parser = argparse.ArgumentParser(description = "record GGreg20 pulse intervals to a csv")
    parser.add_argument("--name", default = DEFAULT_NAME, help = "file name without the extension")
    parser.add_argument("--dir", dest = "out_dir", default = DEFAULT_DIR, help = "folder to write into")
    parser.add_argument("--duration", type = float, default = 3600, help = "seconds to record")
    parser.add_argument("--port", default = None, help = "serial port, defaults to the device default")
    args = parser.parse_args()
    record(name = args.name, out_dir = args.out_dir, duration = args.duration, port = args.port)


if __name__ == "__main__":
    main()
    