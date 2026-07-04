# This is just to check that the radiacode is connected and readable, over usb by default or over bluetooth if specified 

import argparse
import time
from proton.Hardware.Detectors.gamma_spectrometer.link import RadiaCodeDevice


def check(bluetooth_mac = None, wait = 10):
    """This will open the detector, prints its id, and then read the spectrum twice to show the counts building up"""
    with RadiaCodeDevice(bluetooth_mac = bluetooth_mac) as device:
        print("connected to", device.get_device_id())

        device.reset() # restart it so the counts we see are from now, not from before
        first = device.read_raw_spectrum()
        print("channels:", len(first.counts))
        print("calibration a0 a1 a2:", first.a0, first.a1, first.a2)
        print("counts right after reset:", sum(first.counts))

        time.sleep(wait) # give it time to gather a few counts first before doing anything else
        second = device.read_raw_spectrum()
        print("counts after", wait, "seconds:", sum(second.counts))
        print("duration the device reports:", second.duration, "seconds")


def main():
    """Main here reads an optional bluetooth mac and wait time off the command line, then runs the check"""
    parser = argparse.ArgumentParser(description = "check a radiacode connection")
    parser.add_argument("--mac", default = None, help = "bluetooth mac, pass it to go over bluetooth instead of usb")
    parser.add_argument("--wait", type = int, default = 10, help = "seconds to wait between the two reads")
    args = parser.parse_args()
    check(bluetooth_mac = args.mac, wait = args.wait)


if __name__ == "__main__":
    main()
