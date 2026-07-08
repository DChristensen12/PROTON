"""This is everything for linking to a radiacode scintillation detector and pulling its spectra in.
As well as a GeneralSpectrumsDevice method for some scenario where you want to use a different gamma spectrometer (or spectrum device)"""

from radiacode import RadiaCode
import time
from typing import NamedTuple
import csv
from pathlib import Path
import proton



class RawSpectrum(NamedTuple):
    """Pulls one spectrum off a device, stamped with when it is read"""
    counts: tuple # counts per channel, so this is the histogram that you see 
    a0: float # calibration constant term, in units of keV
    a1: float # calibration linear term, in units of keV per channel
    a2: float # calibration quadratic term, in units of keV per channel squared
    duration: float # seconds the spectrum has been building since the last reset
    wall_time: float # unix time
    monotonic: float # a clock that never jumps back, used for intervals


class GeneralSpectrumDevice:
    """
    General device method for gamma spectrometers, and for spectra producing devices in general.
    It replays stored spectra, or ones you hand it via your device, as the same RawSpectrum the real device gives.
    A file is one whole spectrum, so one file replays as one read. Point load at another file format
    with your own parser, or hand it RawSpectrum objects straight, so you can use it with no Radiacode
    or with any other spectrum device.
    """

    DEFAULT_DATA_DIR = Path(proton.__file__).resolve().parent / "default_data" / "gamma_spectrometer"  # the reference spectra shipped in the package, the same folder record_spectrum writes to
    HEADER_FIELDS = ("a0", "a1", "a2", "duration", "wall_time", "monotonic")  # header keys a spectrum file in our own format carries, the calibration and timing fields of RawSpectrum
    __slots__ = ("_counts", "_a0", "_a1", "_a2", "_duration", "_wall_time", "_monotonic", "_cursor", "_reader")

    def __init__(self, data_dir = None, reader = None, spectra = None):
        """Takes RawSpectrum objects, a live reader, loads the spectra in data_dir, or falls back to the bundled ones"""
        self._counts = []
        self._a0 = []
        self._a1 = []
        self._a2 = []
        self._duration = []
        self._wall_time = []
        self._monotonic = []
        self._cursor = 0
        self._reader = reader
        if reader is not None:
            return
        if spectra is not None:
            self._load_spectra(spectra)
            return
        self.load(self.DEFAULT_DATA_DIR if data_dir is None else data_dir) # no reader or handed spectra means we use the data files

    def load(self, data_dir, parser = None, pattern = "*.csv"):
        """Reads every matching file in data_dir in sorted name order, one file per spectrum. Pass your
        own parser to read a format other than ours, and pattern to match its extension. Called again it
        swaps the dataset instead of stacking, and a missing folder is a no op.
        """
        folder = Path(data_dir)
        if not folder.is_dir():
            return
        read = parser if parser is not None else self._read_file  # drop in your own parser for another format
        spectra = [read(path) for path in sorted(folder.glob(pattern))]
        self._load_spectra(spectra)

    def _load_spectra(self, spectra):
        """Fills the replay lists from an iterable of RawSpectrum and rewinds. Every source funnels
        through here, so any device reaches replay by handing over RawSpectrum.
        """
        counts, a0, a1, a2, duration, wall_time, monotonic = [], [], [], [], [], [], []
        for s in spectra:
            counts.append(tuple(s.counts))
            a0.append(float(s.a0))
            a1.append(float(s.a1))
            a2.append(float(s.a2))
            duration.append(float(s.duration))
            wall_time.append(float(s.wall_time))
            monotonic.append(float(s.monotonic))
        # swap the fresh dataset in and rewind
        self._counts = counts
        self._a0, self._a1, self._a2 = a0, a1, a2
        self._duration, self._wall_time, self._monotonic = duration, wall_time, monotonic
        self._cursor = 0

    def _read_file(self, path):
        """Parses one spectrum file in our own format into a RawSpectrum, the header values then the counts column"""
        header = {}
        counts = []
        seen_table = False
        with Path(path).open(newline = "") as f:
            for row in f:
                row = row.rstrip("\r\n")  # csv rows carry crlf, the header lines just lf
                if row.startswith("#"):
                    parts = row[1:].split()  # drop the hash, first token is the key
                    if len(parts) >= 1:
                        header[parts[0]] = parts[1] if len(parts) >= 2 else ""
                    continue
                if row == "channel,counts":
                    seen_table = True
                    continue
                if seen_table and row:
                    counts.append(int(row.split(",")[1]))  # just the count, rows are already in channel order
        for key in self.HEADER_FIELDS:
            if key not in header:
                raise ValueError("spectrum file " + str(path) + " is missing the " + key + " header")
        if not seen_table:
            raise ValueError("spectrum file " + str(path) + " has no channel,counts table")
        return RawSpectrum(
            counts = tuple(counts),
            a0 = float(header["a0"]),
            a1 = float(header["a1"]),
            a2 = float(header["a2"]),
            duration = float(header["duration"]),
            wall_time = float(header["wall_time"]),
            monotonic = float(header["monotonic"]),
        )

    def read_raw_spectrum(self):
        """Hands back one spectrum, live from the reader if there is one, otherwise the next replayed file"""
        if self._reader is not None:
            return self._reader()  # live mode, so the cursor never moves
        if len(self) == 0:
            raise RuntimeError("no spectrum data loaded")
        if self._cursor >= len(self):
            raise RuntimeError("replay is done, every loaded spectrum has been read")
        i = self._cursor
        self._cursor += 1
        return RawSpectrum(
            counts = self._counts[i],
            a0 = self._a0[i],
            a1 = self._a1[i],
            a2 = self._a2[i],
            duration = self._duration[i],
            wall_time = self._wall_time[i],
            monotonic = self._monotonic[i],
        )

    def reset(self):
        """Rewinds to the first spectrum so a finished replay can run again"""
        self._cursor = 0

    def get_device_id(self):
        """Names itself as a replay stand in with how many spectra it holds"""
        return "general spectrum replay, " + str(len(self)) + " spectra"

    def __len__(self):
        """How many spectra are loaded"""
        return len(self._counts)

    def _check_replace(self, column):
        """Guards a replace, the data has to be loaded and the new column has to match its length"""
        if len(self) == 0:
            raise ValueError("load spectra before replacing a column")
        if len(column) != len(self):
            raise ValueError("replacement has " + str(len(column)) + " values but there are " + str(len(self)) + " spectra")

    def replace_counts(self, counts):
        """Swaps the count histograms, each cast to a tuple of ints"""
        self._check_replace(counts)
        self._counts = [tuple(int(c) for c in one) for one in counts]

    def replace_a0(self, a0):
        """Swaps the a0 column, cast to float"""
        self._check_replace(a0)
        self._a0 = [float(v) for v in a0]

    def replace_a1(self, a1):
        """Swaps the a1 column, cast to float"""
        self._check_replace(a1)
        self._a1 = [float(v) for v in a1]

    def replace_a2(self, a2):
        """Swaps the a2 column, cast to float"""
        self._check_replace(a2)
        self._a2 = [float(v) for v in a2]

    def replace_duration(self, duration):
        """Swaps the duration column, cast to float"""
        self._check_replace(duration)
        self._duration = [float(v) for v in duration]

    def replace_wall_time(self, wall_time):
        """Swaps the wall_time column, cast to float"""
        self._check_replace(wall_time)
        self._wall_time = [float(v) for v in wall_time]

    def replace_monotonic(self, monotonic):
        """Swaps the monotonic column, cast to float"""
        self._check_replace(monotonic)
        self._monotonic = [float(v) for v in monotonic]

    @classmethod
    def from_example(cls):
        """Loads the reference spectra shipped in the package, the no hardware door"""
        return cls()  # the default data_dir already points at the default spectra data

    @classmethod
    def from_spectra(cls, spectra):
        """Builds a device straight from RawSpectrum objects you built yourself, whatever device they
        came from. Parse your own file however you like into RawSpectrum, hand me the list, and it
        replays like any other.
        """
        return cls(spectra = list(spectra))

    @classmethod
    def from_reader(cls, counts_reader, a0 = 0.0, a1 = 0.0, a2 = 0.0, duration_reader = None):
        """Builds a live device from your own read function, for a spectrometer PROTON does not have a special class for. 
        counts_reader gives one histogram, duration_reader the seconds it covers. Calibration stays fixed since it does belong
        to the detector in a sense, and we stamp both clocks at read time.
        """
        def reader():
            wall_time = time.time()
            monotonic = time.monotonic()
            counts = tuple(int(c) for c in counts_reader())
            duration = float(duration_reader()) if duration_reader is not None else 0.0
            return RawSpectrum(
                counts = counts,
                a0 = float(a0),
                a1 = float(a1),
                a2 = float(a2),
                duration = duration,
                wall_time = wall_time,
                monotonic = monotonic,
            )
        return cls(reader = reader)

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
