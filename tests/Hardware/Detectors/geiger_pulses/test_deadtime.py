"""Tests for deadtime.py, the offline resolving-time correction for a geiger pulse dt_us series.

Uses intervals built by hand and the bundled background reference recording.
"""

import proton
import csv
from pathlib import Path
import pytest
from proton.Hardware.Detectors.geiger_pulses.deadtime import correct, split_artifacts

BACKGROUND_CSV = Path(proton.__file__).resolve().parent / "default_data" / "geiger_pulses" / "background_room.csv"

def _read_dt_us(path):
    """Return just the dt_us column from a recorded pulse csv."""
    with path.open(newline = "") as f:
        return [int(row["dt_us"]) for row in csv.DictReader(f)]

class TestTubeChoice:
    """Tests that the tube name selects the dead time."""

    def test_sbm20_uses_its_own_floor(self):
        """Test that 185us is an artifact for the sbm20's 190us floor but real for the j305's 180us floor."""
        real, artifacts = split_artifacts([185], tube = "sbm20")
        assert artifacts == [185]
        real, artifacts = split_artifacts([185], tube = "j305")
        assert real == [185]

class TestSplitArtifacts:
    """Tests for splitting real intervals from sub-dead-time artifacts (namely, when a single particle is
    counted twice).
    """

    def test_below_dead_time_is_an_artifact(self):
        """Test that a 150us gap, under the j305's 180us dead time, lands in artifacts not real."""
        real, artifacts = split_artifacts([150, 2000], tube = "j305")
        assert real == [2000]
        assert artifacts == [150]

    def test_unknown_tube_raises(self):
        """Test that a tube name outside DEAD_TIME_US raises rather than defaulting."""
        with pytest.raises(ValueError):
            split_artifacts([1000], tube = "not_a_tube")

class TestModelLimits:
    """Tests for where the model stops being usable."""

    def test_saturation_raises(self):
        """Test that intervals at exactly the dead time, which put n*tau at one, raise instead of dividing by zero."""
        with pytest.raises(ValueError):
            correct([180, 180, 180], tube = "j305")

class TestCorrect:
    """Tests for correct, the double-count cut plus the non-paralyzable rate correction."""

    def test_known_series_counts_and_artifacts(self):
        """Test that a hand-built series with one artifact reports that split."""
        report = correct([150, 1000, 2000, 3000], tube = "j305")
        assert report.registered == 4
        assert report.artifacts == 1
        assert report.true_counts == 3

    def test_empty_after_cut_does_not_divide_by_zero(self):
        """Test that every interval below the dead time returns a report of all zeros rather than raising."""
        report = correct([50, 90, 120], tube = "j305")
        assert report.true_counts == 0
        assert report.observed_cps == 0.0
        assert report.corrected_cps == 0.0

    def test_observed_rate_matches_the_interval_spacing(self):
        """Test that N intervals of D microseconds each give an observed rate close to 1e6 / D."""
        d = 5000
        report = correct([d] * 200, tube = "j305")
        assert report.observed_cps == pytest.approx(1_000_000 / d, rel = 1e-9)

    def test_background_room_regression(self):
        """Test the correction against the bundled background recording, a real (not synthetic)
        dataset whose expected error counts are already known: 1353 registered, 95 double-counted,
        an artifact fraction near 7%.
        """
        intervals = _read_dt_us(BACKGROUND_CSV)
        report = correct(intervals, tube = "j305")
        assert report.registered == 1353
        assert report.artifacts == 95
        assert report.true_counts == 1258
        assert report.artifact_fraction == pytest.approx(0.070, abs = 5e-4)
        assert report.correction_factor == pytest.approx(1.000063, abs = 1e-5)
