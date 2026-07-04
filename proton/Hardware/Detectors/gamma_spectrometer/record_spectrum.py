"""Records a spectrum off a radiacode and writes it to disk. It resets the histogram, lets it build up,
and keeps re-saving the latest one, so if the device drops out partway we can still keep what it gathered."""

import argparse
import csv
import time
from pathlib import Path
import proton
from proton.Hardware.Detectors.gamma_spectrometer.link import RadiaCodeDevice


DEFAULT_DATA = Path(proton.__file__).resolve().parent / "default_data" / "gamma_spectrometer" # where a spectrum lands by default. it sits inside the package so it ships along with everything else
DEFAULT_NAME = "spectrum.csv" # the file name a run falls back to when you do not give it one of your own
DURATION = 3600 # how long to gather for in seconds
SAVE_INTERVAL = 30 # how often to re-save while it is gathering in seconds


def write_spectrum(spectrum, out_path, device_id):
    """Writes one spectrum out to out_path, a small header of metadata first, then the channel and counts table"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents = True, exist_ok = True)
    tmp = out_path.with_name(out_path.name + ".tmp") # write into a temp file first so a crash mid write cannot wreck the real one
    with tmp.open("w", newline = "") as f:
        f.write("# device " + device_id + "\n")
        f.write("# wall_time " + str(spectrum.wall_time) + "\n")
        f.write("# monotonic " + str(spectrum.monotonic) + "\n")
        f.write("# duration " + str(spectrum.duration) + "\n")
        f.write("# a0 " + str(spectrum.a0) + "\n")
        f.write("# a1 " + str(spectrum.a1) + "\n")
        f.write("# a2 " + str(spectrum.a2) + "\n")
        writer = csv.writer(f)
        writer.writerow(("channel", "counts"))
        for channel, count in enumerate(spectrum.counts):
            writer.writerow((channel, count))
    tmp.replace(out_path) # swap the finished file in once it is all the way written


def record(name = None, directory = None, duration = DURATION, save_interval = SAVE_INTERVAL, bluetooth_mac = None):
    """This function resets the histogram, gathers for duration seconds, and keeps re-saving the latest spectrum as it goes.
    name is the file to write, and leaving it out just uses the default name in the default folder."""
    name = name if name is not None else DEFAULT_NAME
    directory = directory if directory is not None else DEFAULT_DATA
    out_path = Path(directory) / name

    with RadiaCodeDevice(bluetooth_mac = bluetooth_mac) as device:
        device_id = device.get_device_id()
        print("recording from", device_id)
        device.reset() # clear it out so the counts start from zero

        start = time.monotonic()
        try:
            while time.monotonic() - start < duration:
                spectrum = device.read_raw_spectrum()
                write_spectrum(spectrum, out_path, device_id) # overwrite with the latest spectrum, which is everything gathered so far
                print("counts so far:", sum(spectrum.counts), "over", round(spectrum.duration), "seconds")
                remaining = duration - (time.monotonic() - start)
                if remaining <= 0:
                    break
                time.sleep(min(save_interval, remaining))
        except Exception as problem:
            # This would mean that the device dropped out on us partway through. whatever we saved last is already safe on disk though,
            # so we just say what happened and keep it, instead of losing the whole gather to a traceback (it would be silly to lose the whole thing)
            print("device stopped partway through, keeping the last saved spectrum:", problem)

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
