"""Records a spectrum off a radiacode and writes it to disk. It resets the histogram, lets it build up,
and keeps re-saving the latest one, so if the device drops out partway we can still keep what it gathered."""

import argparse
from pathlib import Path
import proton
from proton.Hardware.Detectors.gamma_spectrometer.link import RadiaCodeDevice
from proton.common.recording import record_snapshot
from proton.common.data_handler import write_spectrum_file


DEFAULT_DATA = Path(proton.__file__).resolve().parent.parent / "data" / "gamma_spectrometer" # where a fresh recording lands by default, kept in the repo root's data folder, out of the package and gitignored, separate from the bundled default_data
DEFAULT_NAME = "spectrum.csv" # the file name a run falls back to when you do not give it one of your own
DURATION = 3600 # how long to gather for in seconds
SAVE_INTERVAL = 30 # how often to re-save while it is gathering in seconds


def write_spectrum(spectrum, out_path, device_id):
    """Writes one spectrum out to out_path, a small header of metadata first, then the channel and counts table.
    The body moved into data_handler's write_spectrum_file so the format lives next to its parser, this
    stays as the name the rest of this file and anyone importing it already uses."""
    write_spectrum_file(spectrum, out_path, device_id)


def record(name = None, directory = None, duration = DURATION, save_interval = SAVE_INTERVAL, bluetooth_mac = None):
    """This function resets the histogram, gathers for duration seconds, and keeps re-saving the latest spectrum as it goes.
    name is the file to write, and leaving it out just uses the default name in the default folder.

    I moved the polling and re-saving into record_snapshot, the shared recorder's counterpart to
    record_samples for a sample that is a whole file rather than one csv row. That means a device
    dropout now surfaces as an OSError or a ProtonError, same as every other detector, instead of
    the bare Exception I used to catch here. The spectrum file itself is never at risk either way,
    since write_spectrum always finishes one file before the next read starts.

    I moved the polling and re-saving into record_snapshot, the shared recorder's counterpart to
    record_samples for a sample that is a whole file rather than one csv row. That means a device
    dropout now surfaces as an OSError or a ProtonError, same as every other detector, instead of
    the bare Exception I used to catch here. The spectrum file itself is never at risk either way,
    since write_spectrum always finishes one file before the next read starts.
    """
    name = name if name is not None else DEFAULT_NAME
    directory = directory if directory is not None else DEFAULT_DATA
    out_path = Path(directory) / name

    with RadiaCodeDevice(bluetooth_mac = bluetooth_mac) as device:
        device_id = device.get_device_id()
        print("recording from", device_id)
        device.reset() # clear it out so the counts start from zero

        def save(spectrum, path):
            """Writes the latest spectrum and reports the counts gathered so far"""
            write_spectrum(spectrum, path, device_id)
            print("counts so far:", sum(spectrum.counts), "over", round(spectrum.duration), "seconds")

        record_snapshot(
            read_one = device.read_raw_spectrum,
            out_path = out_path,
            duration = duration,
            poll_interval = save_interval,
            write = save,
        )

    print("done, wrote", out_path)


def main():
    """Main here just reads the run settings off the command line and records one spectrum"""
    parser = argparse.ArgumentParser(description = "record a spectrum from a radiacode")
    parser.add_argument("--name", default = DEFAULT_NAME, help = "file name to write, leave it out to use the default")
    parser.add_argument("--dir", default = str(DEFAULT_DATA), help = "folder to write into")
    parser.add_argument("--duration", type = float, default = DURATION, help = "how long to gather, in seconds")
    parser.add_argument("--mac", default = None, help = "bluetooth mac, pass it to go over bluetooth instead of usb")
    args = parser.parse_args()

    try:
        record(name = args.name, directory = args.dir, duration = args.duration, bluetooth_mac = args.mac)
    except KeyboardInterrupt:
        print("stopped early, the last saved spectrum is kept")


if __name__ == "__main__":
    main()
