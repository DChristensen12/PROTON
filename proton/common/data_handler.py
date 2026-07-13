"""
data_handler.py deals with common data handling across all aspects of the project.
It also enables the ability to add other types of data into PROTON that were not specified.

Everything regarding data handling goes through here. 
Hardware may import this file, but this file never imports Hardware. 
Times are relative float64 seconds from acquisition start, t0 is the wall clock unix time of that start (None when unknown).
TODO: Make a DataHandler collection class once needed"""

import csv
from pathlib import Path
import numpy as np
from proton.common.exceptions import ProtonError


class SpectrumError(ProtonError):
    """Raised when a spectrum source cannot be loaded, read, or parsed"""


SPECTRUM_HEADER_FIELDS = ("a0", "a1", "a2", "duration", "wall_time", "monotonic")  # header keys a spectrum file in our own format has


def read_spectrum_file(path):
    """Parses one spectrum file in our own format, the header values then the counts column.
    Returns a dict whose keys line up with RawSpectrum's fields, so the device side can just
    unpack it, and the container side can read it with no Hardware import.
    """
    path = Path(path)
    header = {}
    counts = []
    seen_table = False
    with path.open(newline = "") as f:
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
    for key in SPECTRUM_HEADER_FIELDS:
        if key not in header:
            raise SpectrumError("spectrum file " + str(path) + " is missing the " + key + " header")
    if not seen_table:
        raise SpectrumError("spectrum file " + str(path) + " has no channel,counts table")
    return {
        "counts": tuple(counts),
        "a0": float(header["a0"]),
        "a1": float(header["a1"]),
        "a2": float(header["a2"]),
        "duration": float(header["duration"]),
        "wall_time": float(header["wall_time"]),
        "monotonic": float(header["monotonic"]),
    }


def write_spectrum_file(spectrum, out_path, device_id):
    """
    Writes one spectrum out to out_path, a small header of metadata first, then the channel
    and counts table. It is next to read_spectrum_file so the format is in one place and
    drift between the two breaks a test instead of a user.
    """
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
    tmp.replace(out_path) # swaps the finished file in once it is all the way written


def _as_times(values):
    """
    Turns the input into a validated float64 relative time array. Times must be
    finite and non decreasing, and we shall raise instead of silently sorting because out
    of order timestamps usually mean a clock bug upstream, and hiding that would
    poison our interval statistics :(((
    """
    times = np.asarray(values, dtype = np.float64)
    if times.ndim != 1:
        raise ProtonError("times must be one dimensional")
    if times.size and not np.all(np.isfinite(times)):
        raise ProtonError("times contain nan or inf")
    if times.size > 1 and np.any(np.diff(times) < 0):
        raise ProtonError("times must be non decreasing, sort or fix the source first")
    return times


def _poisson_sigma(counts):
    """Poisson uncertainty on raw counts, sqrt(N) with a floor of one count. The
    floor for empty bins follows becquerel's convention.
    """
    return np.maximum(np.sqrt(counts), 1.0)


class RadiationData:
    """The base every measurement container inherits from.  
    Each subclass keeps whatever numpy shape is natural and just
    provides the _times() hook. More gets added here only when something needs it.
    """

    __slots__ = ("detector_id", "t0", "metadata")

    def __init__(self, detector_id = None, t0 = None, metadata = None):
        """Identity and clock anchor shared by all containers. detector_id names the
        source, t0 anchors relative times to the wall clock (None means unknown), and
        metadata is a free dict for things like position or calibration notes.
        """
        self.detector_id = detector_id
        self.t0 = None if t0 is None else float(t0)
        self.metadata = dict(metadata) if metadata else {}

    def _times(self):
        """Subclasses return their relative time array here."""
        raise ProtonError(type(self).__name__ + " does not provide times")

    def __len__(self):
        """Number of samples held. These containers are static."""
        return self._times().size

    def time_span(self):
        """(first, last) relative time in seconds, or (None, None) when empty."""
        times = self._times()
        if times.size == 0:
            return (None, None)
        return (float(times[0]), float(times[-1]))

    def duration(self):
        """Seconds between first and last sample, zero when fewer than two."""
        first, last = self.time_span()
        if first is None:
            return 0.0
        return last - first

    def slice(self, start, stop):
        """A new container holding samples with start <= time < stop. Times stay
        relative to the original t0, so slices from one run still line up.
        """
        raise ProtonError(type(self).__name__ + " does not implement slice yet")

    def to_frame(self):
        """The pandas export seam, one tidy DataFrame per container. pandas is
        imported lazily so the core package never requires it.
        """
        raise ProtonError(type(self).__name__ + " does not implement to_frame yet")


def _pandas():
    """This is just a Lazy pandas import so it stays an optional dependency."""
    try:
        import pandas
    except ImportError:
        raise ProtonError("to_frame needs pandas, install it or use the numpy arrays directly")
    return pandas


class PulseTrain(RadiationData):
    """Individual pulse arrival times from a counting tube, the rawest signal. This
    is the point process the diffusion model (to be added later) trains on, so the times are
    kept exactly as given, no binning and no debounce.
    """

    __slots__ = ("times",)

    def __init__(self, times, detector_id = None, t0 = None, metadata = None):
        """Wraps an array of relative arrival times in seconds."""
        super().__init__(detector_id, t0, metadata)
        self.times = _as_times(times)

    @classmethod
    def from_intervals(cls, intervals, **kwargs):
        """Builds a train from inter arrival times, first pulse at intervals[0]."""
        intervals = np.asarray(intervals, dtype = np.float64)
        return cls(np.cumsum(intervals), **kwargs)

    @classmethod
    def from_csv(cls, path, column = "time_s", **kwargs):
        """Reads arrival times out of one csv by column name. Column order in the
        file does not matter, only the header name does, same rule the recorder
        follows when writing.
        """
        path = Path(path)
        times = []
        with path.open(newline = "") as f:
            for row in csv.DictReader(f):
                if column not in row:
                    raise ProtonError("no column named " + column + " in " + str(path))
                times.append(float(row[column]))
        return cls(times, **kwargs)

    def _times(self):
        """The arrival times themselves."""
        return self.times

    def delta_t(self):
        """Inter arrival times."""
        return np.diff(self.times)

    def slice(self, start, stop):
        """Pulses with start <= time < stop, times still relative to t0."""
        keep = (self.times >= start) & (self.times < stop)
        return PulseTrain(self.times[keep], self.detector_id, self.t0, self.metadata)

    def binned(self, dt):
        """Counts the train into fixed width bins and returns a CountSeries. A trailing
        partial bin is dropped rather than reported, a short bin would show up as a
        fake dip in rate.
        """
        if dt <= 0:
            raise ProtonError("bin width must be positive")
        first, last = self.time_span()
        if first is None:
            return CountSeries([], [], [], self.detector_id, self.t0, self.metadata)
        n_bins = int((last - first) // dt)
        if n_bins == 0:
            return CountSeries([], [], [], self.detector_id, self.t0, self.metadata)
        edges = first + dt * np.arange(n_bins + 1)
        counts, _ = np.histogram(self.times, bins = edges)
        return CountSeries(edges[1:], np.full(n_bins, dt), counts,
                           self.detector_id, self.t0, self.metadata)

    def to_frame(self):
        """One row per pulse."""
        pd = _pandas()
        return pd.DataFrame({"time_s": self.times})


class CountSeries(RadiationData):
    """Counts accumulated per interval, what a polled counter gives.
    Times mark interval ends, durations their lengths, counts what landed inside.
    Rates and their Poisson uncertainties are derived on access, never stored, so
    they cannot get out of sync with the raw counts.
    """

    __slots__ = ("times", "durations", "counts")

    def __init__(self, times, durations, counts, detector_id = None, t0 = None, metadata = None):
        """Wraps the three parallel arrays after checking they agree."""
        super().__init__(detector_id, t0, metadata)
        self.times = _as_times(times)
        self.durations = np.asarray(durations, dtype = np.float64)
        self.counts = np.asarray(counts, dtype = np.float64)
        if not (self.times.size == self.durations.size == self.counts.size):
            raise ProtonError("times, durations and counts must be the same length")
        if self.times.size and np.any(self.durations <= 0):
            raise ProtonError("every interval duration must be positive")

    @classmethod
    def from_cumulative(cls, times, totals, **kwargs):
        """Builds a series from running totals, the shape RawSample reports. Differencing
        turns cumulative counts into counts per interval, so the first sample only sets
        the baseline and produces no bin.
        """
        times = _as_times(times)
        totals = np.asarray(totals, dtype = np.float64)
        if times.size != totals.size:
            raise ProtonError("times and totals must be the same length")
        if times.size < 2:
            return cls([], [], [], **kwargs)
        if np.any(np.diff(totals) < 0):
            raise ProtonError("cumulative totals decreased, the counter reset mid run")
        return cls(times[1:], np.diff(times), np.diff(totals), **kwargs)

    @classmethod
    def from_csv(cls, path, **kwargs):
        """Reads a recorder csv from a counts device into a series. Expects the
        pulse_count and monotonic columns the recorder writes, and t0 comes off the
        first wall_time unless the caller passes their own.
        """
        path = Path(path)
        totals, mono, wall = [], [], []
        with path.open(newline = "") as f:
            for row in csv.DictReader(f):
                if "pulse_count" not in row or "monotonic" not in row:
                    raise ProtonError(str(path) + " is missing pulse_count or monotonic columns")
                totals.append(float(row["pulse_count"]))
                mono.append(float(row["monotonic"]))
                if "wall_time" in row:
                    wall.append(float(row["wall_time"]))
        if not mono:
            return cls([], [], [], **kwargs)
        if "t0" not in kwargs or kwargs["t0"] is None:
            kwargs["t0"] = wall[0] if wall else None
        rel = np.asarray(mono) - mono[0]  # monotonic never jumps, so it carries the intervals
        return cls.from_cumulative(rel, totals, **kwargs)

    def _times(self):
        """Interval end times."""
        return self.times

    @property
    def rate_vals(self):
        """Count rate per interval in counts per second."""
        return self.counts / self.durations

    @property
    def rate_uncs(self):
        """Poisson one sigma on each rate."""
        return _poisson_sigma(self.counts) / self.durations

    def slice(self, start, stop):
        """Intervals ending with start <= time < stop."""
        keep = (self.times >= start) & (self.times < stop)
        return CountSeries(self.times[keep], self.durations[keep], self.counts[keep],
                           self.detector_id, self.t0, self.metadata)

    def to_frame(self):
        """One row per interval with rate and uncertainty alongside the raw counts."""
        pd = _pandas()
        return pd.DataFrame({
            "time_s": self.times,
            "duration_s": self.durations,
            "counts": self.counts,
            "rate_cps": self.rate_vals,
            "rate_unc_cps": self.rate_uncs,
        })


class SpectrumSeries(RadiationData):
    """Channel spectra snapshotted over time, times by channels in one array.
    calibration holds polynomial coefficients (a0, a1, a2, ...) mapping channel to
    keV, the same shape the Radiacode reports. None means uncalibrated, and asking
    for energies then raises instead of trying to guess or erroring.
    """

    __slots__ = ("times", "counts", "calibration", "durations")

    def __init__(self, times, counts, calibration = None, durations = None,
                 detector_id = None, t0 = None, metadata = None):
        """Wraps snapshot times and the 2d counts array behind them. durations is optional,
        it carries how many seconds each snapshot gathered for, which rate work will need."""
        super().__init__(detector_id, t0, metadata)
        self.times = _as_times(times)
        self.counts = np.atleast_2d(np.asarray(counts, dtype = np.float64))
        if self.times.size == 0 and self.counts.size == 0:
            self.counts = self.counts.reshape(0, 0)
        if self.counts.shape[0] != self.times.size:
            raise SpectrumError("need one row of counts per snapshot time")
        self.calibration = None if calibration is None else tuple(float(c) for c in calibration)
        if durations is None:
            self.durations = None
        else:
            self.durations = np.asarray(durations, dtype = np.float64)
            if self.durations.size != self.times.size:
                raise SpectrumError("need one duration per snapshot time")

    @classmethod
    def from_spectra(cls, times, counts, **kwargs):
        """Same as the constructor, kept as a named door to match the other containers."""
        return cls(times, counts, **kwargs)

    @classmethod
    def from_file(cls, path, **kwargs):
        """One recorded spectrum file becomes a one snapshot series, the zero hardware way
        to anything record_spectrum wrote. Each file is its own run with its own clocks, so
        comparing runs means one series per file, not one series of many files."""
        d = read_spectrum_file(path)
        if "t0" not in kwargs or kwargs["t0"] is None:
            kwargs["t0"] = d["wall_time"]
        return cls([0.0], [d["counts"]], calibration = (d["a0"], d["a1"], d["a2"]),
                   durations = [d["duration"]], **kwargs)

    @classmethod
    def from_raw_spectra(cls, spectra, **kwargs):
        """Builds a series from RawSpectrum shaped objects out of one run, anything with the
        counts, calibration, duration and clock fields works. Times come off monotonic relative
        to the first snapshot and t0 off the first wall_time. Every snapshot has to share one
        calibration and one channel count, mixing runs is exactly the mistake that check catches."""
        spectra = list(spectra)
        if not spectra:
            return cls([], np.empty((0, 0)), **kwargs)
        cal = (float(spectra[0].a0), float(spectra[0].a1), float(spectra[0].a2))
        n_ch = len(spectra[0].counts)
        for one in spectra:
            if (float(one.a0), float(one.a1), float(one.a2)) != cal:
                raise SpectrumError("snapshots carry different calibrations, these are not one run")
            if len(one.counts) != n_ch:
                raise SpectrumError("snapshots carry different channel counts, these are not one run")
        if "t0" not in kwargs or kwargs["t0"] is None:
            kwargs["t0"] = float(spectra[0].wall_time)
        first = float(spectra[0].monotonic)
        return cls([float(one.monotonic) - first for one in spectra],
                   [one.counts for one in spectra],
                   calibration = cal,
                   durations = [float(one.duration) for one in spectra],
                   **kwargs)

    def _times(self):
        """Snapshot times."""
        return self.times

    @property
    def n_channels(self):
        """Channels per snapshot."""
        return self.counts.shape[1] if self.counts.size else 0

    @property
    def counts_uncs(self):
        """Poisson one sigma per channel per snapshot."""
        return _poisson_sigma(self.counts)

    def energies(self):
        """Energy in keV for each channel center from the calibration polynomial."""
        if self.calibration is None:
            raise SpectrumError("this spectrum has no energy calibration")
        channels = np.arange(self.n_channels, dtype = np.float64)
        energy = np.zeros_like(channels)
        for power, coeff in enumerate(self.calibration):
            energy += coeff * channels ** power
        return energy

    def slice(self, start, stop):
        """Snapshots with start <= time < stop."""
        keep = (self.times >= start) & (self.times < stop)
        durations = None if self.durations is None else self.durations[keep]
        return SpectrumSeries(self.times[keep], self.counts[keep], self.calibration, durations,
                              self.detector_id, self.t0, self.metadata)

    def to_frame(self):
        """Tidy long format, one row per time and channel pair. This gets big for long
        runs, it exists as the export seam, the models keep using the 2d array directly.
        """
        pd = _pandas()
        n_t, n_ch = self.counts.shape if self.counts.size else (0, 0)
        frame = {
            "time_s": np.repeat(self.times, n_ch),
            "channel": np.tile(np.arange(n_ch), n_t),
            "counts": self.counts.ravel(),
        }
        if self.durations is not None and n_ch:
            frame["duration_s"] = np.repeat(self.durations, n_ch)
        if self.calibration is not None and n_ch:
            frame["energy_kev"] = np.tile(self.energies(), n_t)
        return pd.DataFrame(frame)
    