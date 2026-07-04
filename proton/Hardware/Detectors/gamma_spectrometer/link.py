"""This is everything for linking to a radiacode scintillation detector and pulling its spectra in.
As well as a GeneralSpectrumsDevice method (I'll add this in later) for some scenario where you want to use a different gamma spectrometer"""

from radiacode import RadiaCode
import time
from typing import NamedTuple


class RawSpectrum(NamedTuple):
    """Pulls one spectrum off a device, stamped with when it is read"""
    counts: tuple # counts per channel, so this is the histogram that you see 
    a0: float # calibration constant term, in units of keV
    a1: float # calibration linear term, in units of keV per channel
    a2: float # calibration quadratic term, in units of keV per channel squared
    duration: float # seconds the spectrum has been building since the last reset
    wall_time: float # unix time
    monotonic: float # a clock that never jumps back, used for intervals


class RadiaCodeDevice:
    """ A wrapper around a radiacode scintillation detector. This opens the usb or bluetooth link, and
    hands back the device id and the timestamped raw spectra."""

    DEFAULT_MODEL = "102" # what i personally have, change it if you are on a 103 or 110

    __slots__ = ("_model", "_rc")

    def __init__(self, bluetooth_mac = None, serial_number = None, model = None, device = None, ignore_firmware_check = False):
        """
        Opens the link to the detector, or use a device object passed in.
        Leave bluetooth_mac out to go over usb, or pass it to go over bluetooth. serial_number picks
        one detector when more than one is plugged in.
        """

        self._model = model if model is not None else self.DEFAULT_MODEL
        if device is not None:
            self._rc = device # uses the object handed to it
        else:
            self._rc = RadiaCode(bluetooth_mac = bluetooth_mac, serial_number = serial_number, ignore_firmware_compatibility_check = ignore_firmware_check)

    def __enter__(self):
        """Lets you use the device in a with block"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Always drop the link on the way out, even when something has failed."""
        self.close()

    def close(self):
        """Let go of the connection so it can be cleaned up. The library has no disconnect of its own,
        so dropping our handle is the most we can do."""
        self._rc = None

    def get_device_id(self):
        """Names the model and serial, so the code that records which detector it used still gets an answer"""
        return "Radiacode " + self._model + " " + self._rc.serial_number()

    def read_raw_spectrum(self):
        """
        Pulls the current spectrum off the device as a RawSpectrum.
        We grab both clocks first so the timestamps sit as close as they can to the actual read. The
        counts are cumulative since the last reset, and the duration says over how long they built up.
        """
        wall_time = time.time()
        monotonic = time.monotonic()
        spectrum = self._rc.spectrum()
        return RawSpectrum(
            counts = tuple(spectrum.counts),
            a0 = spectrum.a0,
            a1 = spectrum.a1,
            a2 = spectrum.a2,
            duration = spectrum.duration.total_seconds(),
            wall_time = wall_time,
            monotonic = monotonic
        )

    def reset(self):
        """Clear the accumulating spectrum so a new, fresh measurement starts from zero counts"""
        self._rc.spectrum_reset()
