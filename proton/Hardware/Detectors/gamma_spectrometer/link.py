"""This is everything for linking to a radiacode scintillation detector and pulling its spectra in.
As well as a GeneralSpectrumsDevice method for some scenario where you want to use a different gamma spectrometer (or spectrum device)"""

import time
from typing import NamedTuple
import csv
from pathlib import Path
import proton
from proton.common import ProtonError
from proton.common.data_handler import SpectrumError, SpectrumSeries, read_spectrum_file, SPECTRUM_HEADER_FIELDS


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
    HEADER_FIELDS = SPECTRUM_HEADER_FIELDS  # the format lives in data_handler now, this stays as the same name it always had
    DEFAULT_POLL_INTERVAL = 30.0  # I copied this from record_spectrum.py's SAVE_INTERVAL, the cadence I already re-read a spectrum at
    __slots__ = ("_spectra", "_cursor", "_reader")

    def __init__(self, data_dir = None, reader = None, spectra = None):
        """Takes RawSpectrum objects, a live reader, loads the spectra in data_dir, or falls back to the bundled ones"""
        self._spectra = [] # one list of RawSpectrum, so adding a field means touching RawSpectrum and nothing else
        self._cursor = 0
        self._reader = reader
        if reader is not None:
            return
        if spectra is not None:
            self._load_spectra(spectra)
            return
        self.load(self.DEFAULT_DATA_DIR if data_dir is None else data_dir) # no reader or handed spectra means we use the data files

    def __enter__(self):
        """Lets you use the device in a with block"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Nothing to release, but included for consistency"""
        return False

    def load(self, data_dir, parser = None, pattern = "*.csv"):
        """Reads every matching file in data_dir in sorted name order, one file per spectrum. Pass your
        own parser to read a format other than ours, and pattern to match its extension. Called again it
        swaps the dataset instead of stacking. I treat a missing folder as a no op, since that's the
        default data path before I've ever recorded anything, but a path that exists and is neither a
        directory nor a file we can read is an error, not a empty load.
        """
        path = Path(data_dir)
        if not path.exists():
            return
        read = parser if parser is not None else self._read_file  # drop in your own parser for another format
        if path.is_dir():
            files = sorted(path.glob(pattern))
        elif path.is_file():
            files = [path]  # one file, one spectrum, same as if I'd pointed load() at a folder holding just this one
        else:
            raise SpectrumError(str(path) + " is neither a file nor a directory")
        spectra = [read(p) for p in files]
        self._load_spectra(spectra)

    def _load_spectra(self, spectra):
        """Normalizes an iterable of RawSpectrum shaped objects into the replay list and rewinds.
        Every source funnels through here, so any device reaches replay by handing over RawSpectrum.
        """
        self._spectra = [
            RawSpectrum(
                counts = tuple(s.counts),
                a0 = float(s.a0),
                a1 = float(s.a1),
                a2 = float(s.a2),
                duration = float(s.duration),
                wall_time = float(s.wall_time),
                monotonic = float(s.monotonic),
            )
            for s in spectra
        ]
        self._cursor = 0

    def _read_file(self, path):
        """Parses one spectrum file in our own format into a RawSpectrum. The parser itself lives
        in data_handler next to the writer, so the format is defined in exactly one place, and its
        dict keys line up with RawSpectrum's fields on purpose."""
        return RawSpectrum(**read_spectrum_file(path))

    def read_raw_spectrum(self):
        """Hands back one spectrum, live from the reader if there is one, otherwise the next replayed file"""
        if self._reader is not None:
            return self._reader()  # live mode, so the cursor never moves
        if len(self) == 0:
            raise SpectrumError("no spectrum data loaded")
        if self._cursor >= len(self):
            raise SpectrumError("replay is done, every loaded spectrum has been read")
        i = self._cursor
        self._cursor += 1
        return self._spectra[i] # already a RawSpectrum, normalized on the way in

    def reset(self):
        """Rewinds to the first spectrum so a finished replay can run again"""
        self._cursor = 0

    def get_device_id(self):
        """Names itself as a live source or a replay stand in with how many spectra it holds"""
        if self._reader is not None:
            return "general spectrum live"
        return "general spectrum replay, " + str(len(self)) + " spectra"

    def __len__(self):
        """How many spectra are loaded

        A live reader gives me no stored spectra to count, so we will raise here rather than answer
        0, which would look like an empty replay instead of a stream.
        """
        if self._reader is not None:
            raise SpectrumError("this source streams, so its length is not known")
        return len(self._spectra)

    def _check_replace(self, column):
        """Guards a replace, the data has to be loaded and the new column has to match its length"""
        if len(self) == 0:
            raise SpectrumError("load spectra before replacing a column")
        if len(column) != len(self):
            raise SpectrumError("replacement has " + str(len(column)) + " values but there are " + str(len(self)) + " spectra")

    def _replace_column(self, field, values, cast):
        """The one place a column swap actually happens, the replace_ methods below just name
        the field and its cast. _replace on the namedtuple keeps every other field untouched."""
        self._check_replace(values)
        self._spectra = [s._replace(**{field: cast(v)}) for s, v in zip(self._spectra, values)]

    def replace_counts(self, counts):
        """Swaps the count histograms, each cast to a tuple of ints"""
        self._replace_column("counts", counts, lambda one: tuple(int(c) for c in one))

    def replace_a0(self, a0):
        """Swaps the a0 column, cast to float"""
        self._replace_column("a0", a0, float)

    def replace_a1(self, a1):
        """Swaps the a1 column, cast to float"""
        self._replace_column("a1", a1, float)

    def replace_a2(self, a2):
        """Swaps the a2 column, cast to float"""
        self._replace_column("a2", a2, float)

    def replace_duration(self, duration):
        """Swaps the duration column, cast to float"""
        self._replace_column("duration", duration, float)

    def replace_wall_time(self, wall_time):
        """Swaps the wall_time column, cast to float"""
        self._replace_column("wall_time", wall_time, float)

    def replace_monotonic(self, monotonic):
        """Swaps the monotonic column, cast to float"""
        self._replace_column("monotonic", monotonic, float)

    def to_series(self, **kwargs):
        """Gives the held spectra over as a SpectrumSeries, the entrance from this device into
        the analysis side. It assumes the snapshots came from one run, and the series checks
        that (one calibration, one channel count, non decreasing clocks) and raises whenever it is handed 
        a deck of unrelated reference spectra, convert those one at a time instead."""
        if self._reader is not None:
            raise SpectrumError("this source streams, record it to files first and load those")
        if "detector_id" not in kwargs:
            kwargs["detector_id"] = self.get_device_id()
        return SpectrumSeries.from_raw_spectra(self._spectra, **kwargs)

    @classmethod
    def from_example(cls):
        """Loads the reference spectra shipped in the package, the no hardware door"""
        return cls()  # the default data_dir already points at the default spectra data

    @classmethod
    def from_spectra(cls, spectra):
        """Builds a device straight from RawSpectrum objects you built yourself, whatever device they
        came from. Parse your own file however you like into RawSpectrum, hand it the list, and it
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
    DEFAULT_POLL_INTERVAL = 30.0 # I copied this from record_spectrum.py's SAVE_INTERVAL, the cadence I already re-read a spectrum at

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
            from radiacode import RadiaCode  # we only need this installed for the real device path
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
