"""check_pulses.py is the smoke test for the pulse chain. It reads a handful of intervals and prints
them, so I can tell the wiring works before starting a long run.

It also counts intervals shorter than the tube dead time. The tube physically cannot fire twice inside
that window, so anything below it is not radiation. It is a loose contact or a bouncing jumper. A clean
rig reports zero.
"""

import argparse

from proton.Hardware.Detectors.geiger_pulses.readout import EspPulseDevice

DEAD_TIME_US = {"j305": 180, "sbm20": 190}


def check(count = 10, port = None, tube = "j305"):
    """Read count intervals, print each one, then report the rate and any impossible gaps"""
    floor = DEAD_TIME_US[tube]
    intervals = []
    with EspPulseDevice(port = port) as device:
        print("reading", count, "pulses from", device.get_device_id())
        for _ in range(count):
            pulse = device.read_raw_pulse()
            print(pulse.pulse_index, pulse.dt_us, "us")
            intervals.append(pulse.dt_us)

    total_us = sum(intervals)
    if total_us > 0:
        cpm = len(intervals) * 60_000_000 / total_us
        print("rate", round(cpm, 1), "cpm")

    impossible = [dt for dt in intervals if dt < floor]
    # I report these rather than filtering them, since a silent filter would hide a bad connection
    if impossible:
        print("warning:", len(impossible), "intervals under the", floor, "us dead time")
        print("that is a wiring artifact, not radiation. check the pulse jumper before recording")
    else:
        print("no intervals under the", floor, "us dead time")

    return intervals


def main():
    """Parse the command line and run the check"""
    parser = argparse.ArgumentParser(description = "smoke test the GGreg20 pulse chain")
    parser.add_argument("--count", type = int, default = 10, help = "how many pulses to read")
    parser.add_argument("--port", default = None, help = "serial port, defaults to the device default")
    parser.add_argument("--tube", default = "j305", choices = sorted(DEAD_TIME_US), help = "which tube is fitted")
    args = parser.parse_args()
    check(count = args.count, port = args.port, tube = args.tube)


if __name__ == "__main__":
    main()
    