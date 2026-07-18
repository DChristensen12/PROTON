"""Tests for data_handler.py, the container layer every detector's analysis path runs through.

Containers here are built from arrays, RawSpectrum-shaped stand-ins, and small temp csvs. No
hardware is used, so this is the one place the containers are exercised directly rather than
through a device parity check.
"""

import csv

import numpy as np
import pytest

from proton.common.data_handler import (
    RadiationData,
    PulseTrain,
    CountSeries,
    SpectrumSeries,
    SpectrumError,
    read_spectrum_file,
    write_spectrum_file,
)
from proton.common.exceptions import ProtonError

rng = np.random.default_rng(4)


class FakeSpectrum:
    """Stand-in for RawSpectrum so the spectrum tests do not import Hardware.

    Holds the seven fields the containers read, with defaults so a test only sets what it cares
    about.
    """

    def __init__(self, counts, a0 = 1.0, a1 = 2.5, a2 = 0.001, duration = 60.0,
                 wall_time = 1000.0, monotonic = 50.0):
        self.counts = counts
        self.a0, self.a1, self.a2 = a0, a1, a2
        self.duration = duration
        self.wall_time = wall_time
        self.monotonic = monotonic


def write_counts_csv(path, rows):
    """Write a counts csv with the header the geiger_counts recorder produces."""
    with path.open("w", newline = "") as f:
        writer = csv.writer(f)
        writer.writerow(["pulse_count", "tube_rate", "wall_time", "monotonic"])
        writer.writerows(rows)


def write_pulse_csv(path, rows):
    """Write a pulse csv with the header the geiger_pulses recorder produces from RawPulse."""
    with path.open("w", newline = "") as f:
        writer = csv.writer(f)
        writer.writerow(["pulse_index", "dt_us", "wall_time", "monotonic"])
        writer.writerows(rows)


class TestValidation:
    """Tests for the checks every container shares through the base class and the time helper."""

    def test_out_of_order_times_raise(self):
        """Test that out-of-order timestamps raise instead of being sorted."""
        with pytest.raises(ProtonError):
            PulseTrain([0.0, 2.0, 1.0])

    def test_nan_times_raise(self):
        """Test that a nan in the times raises rather than building the container."""
        with pytest.raises(ProtonError):
            PulseTrain([0.0, float("nan"), 1.0])

    def test_base_class_does_not_stand_alone(self):
        """Test that RadiationData, the base contract rather than a container, raises on time_span."""
        with pytest.raises(ProtonError):
            RadiationData().time_span()

    def test_metadata_and_t0_survive(self):
        """Test that detector_id, t0, and metadata are carried as given, with t0 cast to float."""
        train = PulseTrain([0.0, 1.0], detector_id = "gg20", t0 = 1000, metadata = {"pos": "bench"})
        assert train.detector_id == "gg20"
        assert train.t0 == 1000.0 and isinstance(train.t0, float)
        assert train.metadata["pos"] == "bench"


class TestPulseTrain:
    """Tests for the PulseTrain container."""

    def test_delta_t_matches_intervals(self):
        """Test that a train built from gaps recovers those same gaps as delta_t."""
        gaps = rng.exponential(0.05, 500)
        train = PulseTrain.from_intervals(gaps)
        assert np.allclose(train.delta_t(), gaps[1:])
        assert len(train) == 500

    def test_slice_keeps_the_relative_clock(self):
        """Test that a window selects arrivals without shifting their times or dropping t0."""
        train = PulseTrain([0.5, 1.5, 2.5, 3.5], t0 = 1000.0)
        window = train.slice(1.0, 3.0)
        assert np.allclose(window.times, [1.5, 2.5])
        assert window.t0 == 1000.0

    def test_binned_drops_the_partial_bin(self):
        """Test that a trailing short bin is dropped rather than reported as a partial rate."""
        train = PulseTrain([0.0, 0.4, 1.1, 1.9, 2.3])
        series = train.binned(1.0)
        assert series.counts.sum() <= len(train)
        assert np.allclose(series.durations, 1.0)

    def test_binned_returns_a_count_series(self):
        """Test that binning a train returns a CountSeries."""
        train = PulseTrain([0.0, 0.2, 0.7, 1.3, 1.8])
        assert isinstance(train.binned(1.0), CountSeries)

    def test_empty_train_is_safe(self):
        """Test that zero pulses gives empty answers rather than raising."""
        train = PulseTrain([])
        assert train.duration() == 0.0
        assert train.delta_t().size == 0

    def test_from_csv_reads_by_column_name(self, tmp_path):
        """Test that from_csv reads a file of absolute times by header name, column order aside."""
        path = tmp_path / "times.csv"
        path.write_text("time_s\n0.1\n0.2\n0.7\n")
        train = PulseTrain.from_csv(path)
        assert np.allclose(train.times, [0.1, 0.2, 0.7])

    def test_from_recorded_sums_the_gaps(self, tmp_path):
        """Test that from_recorded sums the recorder's microsecond gaps into second-scale arrivals."""
        path = tmp_path / "pulses.csv"
        write_pulse_csv(path, [
            [1, 500_000, 1000.0, 50.0],
            [2, 250_000, 1000.5, 50.5],
            [3, 1_000_000, 1001.5, 51.5],
        ])
        train = PulseTrain.from_recorded(path)
        assert np.allclose(train.times, [0.5, 0.75, 1.75])
        assert np.allclose(train.delta_t(), [0.25, 1.0])
        assert train.t0 == 1000.0

    def test_from_recorded_missing_column_is_loud(self, tmp_path):
        """Test that a recorded csv without a dt_us column raises and names the file."""
        path = tmp_path / "wrong.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(ProtonError):
            PulseTrain.from_recorded(path)

    def test_from_recorded_empty_is_safe(self, tmp_path):
        """Test that a recorded header with no rows gives an empty train with t0 unset."""
        path = tmp_path / "empty.csv"
        write_pulse_csv(path, [])
        train = PulseTrain.from_recorded(path)
        assert len(train) == 0
        assert train.t0 is None

    def test_to_frame_is_one_row_per_pulse(self):
        """Test that the pandas export has one row per arrival."""
        frame = PulseTrain([0.1, 0.9]).to_frame()
        assert list(frame["time_s"]) == [0.1, 0.9]


class TestCountSeries:
    """Tests for the CountSeries container and the rates it derives."""

    def test_from_cumulative_differences_the_totals(self):
        """Test that running totals become counts per interval, with the first sample setting the baseline."""
        series = CountSeries.from_cumulative([0.0, 1.0, 2.0, 3.0], [10, 15, 15, 22])
        assert np.allclose(series.counts, [5, 0, 7])
        assert len(series) == 3

    def test_counter_reset_is_loud(self):
        """Test that a total that drops raises instead of being read as a device reset."""
        with pytest.raises(ProtonError):
            CountSeries.from_cumulative([0.0, 1.0, 2.0], [10, 20, 5])

    def test_poisson_uncertainty_with_a_floor(self):
        """Test that rates carry sqrt-N sigma computed on access, with an empty bin floored at one count."""
        series = CountSeries([1.0, 2.0], [1.0, 1.0], [100, 0])
        assert np.allclose(series.rate_vals, [100.0, 0.0])
        assert np.allclose(series.rate_uncs, [10.0, 1.0])

    def test_mismatched_columns_raise(self):
        """Test that times, durations, and counts of different lengths raise rather than build."""
        with pytest.raises(ProtonError):
            CountSeries([1.0, 2.0], [1.0], [5])

    def test_from_csv_reads_the_recorder_format(self, tmp_path):
        """Test that from_csv reads the counts recorder header, differencing pulse_count into per-interval counts."""
        path = tmp_path / "counts.csv"
        write_counts_csv(path, [
            [100, 30.0, 1700000000.0, 50.0],
            [103, 30.0, 1700000001.0, 51.0],
            [109, 30.0, 1700000002.0, 52.0],
        ])
        series = CountSeries.from_csv(path)
        assert np.allclose(series.counts, [3, 6])
        assert series.t0 == 1700000000.0

    def test_slice_selects_intervals(self):
        """Test that a window keeps the intervals ending inside it, with columns staying aligned."""
        series = CountSeries([1.0, 2.0, 3.0], [1.0, 1.0, 1.0], [5, 6, 7])
        window = series.slice(1.5, 3.5)
        assert np.allclose(window.counts, [6, 7])

    def test_to_frame_carries_the_uncertainty(self):
        """Test that the export puts the rate and its sigma next to the raw counts."""
        frame = CountSeries([1.0], [1.0], [25]).to_frame()
        assert float(frame["rate_unc_cps"].iloc[0]) == 5.0


class TestSpectrumSeries:
    """Tests for the SpectrumSeries container and its calibration."""

    def test_shape_agreement_is_enforced(self):
        """Test that mismatched snapshot times and count rows raise rather than build."""
        with pytest.raises(SpectrumError):
            SpectrumSeries([0.0, 1.0], np.zeros((3, 8)))

    def test_energies_from_the_calibration_polynomial(self):
        """Test that channel-to-keV follows a0 + a1*c + a2*c**2, the shape the Radiacode reports."""
        spec = SpectrumSeries([0.0], np.zeros((1, 4)), calibration = (1.0, 2.0, 0.5))
        assert np.allclose(spec.energies(), [1.0, 3.5, 7.0, 11.5])

    def test_uncalibrated_energies_raise(self):
        """Test that energies raises when no calibration is set."""
        spec = SpectrumSeries([0.0], np.zeros((1, 4)))
        with pytest.raises(SpectrumError):
            spec.energies()

    def test_counts_uncertainty_is_poisson(self):
        """Test that per-channel sigma is sqrt N with the same one-count floor as CountSeries."""
        spec = SpectrumSeries([0.0], [[100, 0, 4]])
        assert np.allclose(spec.counts_uncs, [10.0, 1.0, 2.0])

    def test_slice_selects_snapshots(self):
        """Test that a window keeps whole snapshots that fall inside it."""
        counts = rng.poisson(5, (3, 16))
        spec = SpectrumSeries([0.0, 10.0, 20.0], counts)
        window = spec.slice(5.0, 25.0)
        assert window.counts.shape == (2, 16)

    def test_from_file_is_one_snapshot(self, tmp_path):
        """Test that one recorded file becomes a one-snapshot series with its clocks and calibration mapped over."""
        path = tmp_path / "spec.csv"
        write_spectrum_file(FakeSpectrum((5, 0, 12, 3), wall_time = 1234.0), path, "test device")
        series = SpectrumSeries.from_file(path)
        assert len(series) == 1
        assert series.t0 == 1234.0
        assert series.durations[0] == 60.0
        assert np.allclose(series.energies(), [1.0, 3.501, 6.004, 8.509])

    def test_from_raw_spectra_maps_the_clocks(self):
        """Test that snapshot times come from monotonic relative to the first, and t0 from the first wall_time."""
        run = [FakeSpectrum((1, 2), monotonic = 50.0, wall_time = 900.0, duration = 10.0),
               FakeSpectrum((3, 4), monotonic = 80.0, wall_time = 930.0, duration = 40.0)]
        series = SpectrumSeries.from_raw_spectra(run, detector_id = "fake")
        assert np.allclose(series.times, [0.0, 30.0])
        assert series.t0 == 900.0
        assert np.allclose(series.durations, [10.0, 40.0])
        assert series.counts.shape == (2, 2)

    def test_mixed_runs_are_refused(self):
        """Test that spectra with different calibrations raise instead of merging into one run."""
        run = [FakeSpectrum((1, 2), a0 = 1.0), FakeSpectrum((3, 4), a0 = 9.0)]
        with pytest.raises(SpectrumError):
            SpectrumSeries.from_raw_spectra(run)

    def test_mixed_channel_counts_are_refused(self):
        """Test that snapshots of different channel widths also raise instead of merging."""
        run = [FakeSpectrum((1, 2, 3)), FakeSpectrum((1, 2))]
        with pytest.raises(SpectrumError):
            SpectrumSeries.from_raw_spectra(run)

    def test_durations_survive_slicing(self):
        """Test that a sliced series keeps the durations of the snapshots it kept."""
        run = [FakeSpectrum((1, 2), monotonic = 0.0, duration = 5.0),
               FakeSpectrum((3, 4), monotonic = 10.0, duration = 15.0)]
        series = SpectrumSeries.from_raw_spectra(run)
        window = series.slice(5.0, 20.0)
        assert np.allclose(window.durations, [15.0])

    def test_to_frame_is_tidy(self):
        """Test that the export is long format, one row per time and channel pair, with energies when calibrated."""
        spec = SpectrumSeries([0.0, 1.0], np.arange(8).reshape(2, 4), calibration = (0.0, 1.0))
        frame = spec.to_frame()
        assert len(frame) == 8
        assert set(frame.columns) == {"time_s", "channel", "counts", "energy_kev"}


class TestSpectrumFileFormat:
    """Tests for the on-disk spectrum format, the read_spectrum_file/write_spectrum_file pair."""

    def test_round_trip(self, tmp_path):
        """Test that what write_spectrum_file writes, read_spectrum_file reads back unchanged."""
        path = tmp_path / "spec.csv"
        write_spectrum_file(FakeSpectrum((5, 0, 12, 3)), path, "test device")
        d = read_spectrum_file(path)
        assert d["counts"] == (5, 0, 12, 3)
        assert (d["a0"], d["a1"], d["a2"]) == (1.0, 2.5, 0.001)
        assert d["duration"] == 60.0

    def test_missing_header_is_loud(self, tmp_path):
        """Test that a file missing a calibration header names the missing key rather than guessing."""
        path = tmp_path / "broken.csv"
        path.write_text("# a0 1\nchannel,counts\r\n0,1\r\n")
        with pytest.raises(SpectrumError):
            read_spectrum_file(path)

    def test_missing_table_is_loud(self, tmp_path):
        """Test that a header with no counts table raises instead of parsing."""
        path = tmp_path / "broken.csv"
        path.write_text("# a0 1\n# a1 1\n# a2 1\n# duration 1\n# wall_time 1\n# monotonic 1\n")
        with pytest.raises(SpectrumError):
            read_spectrum_file(path)

    def test_leaves_no_temp_file_behind(self, tmp_path):
        """Test that the temp file written during the save is gone, leaving just the real file."""
        path = tmp_path / "spec.csv"
        write_spectrum_file(FakeSpectrum((1, 2, 3)), path, "dev")
        assert path.exists()
        assert not (tmp_path / "spec.csv.tmp").exists()
