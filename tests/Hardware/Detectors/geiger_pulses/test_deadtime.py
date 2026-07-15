""" 
These are all the tests for the deadtime.py file, the offline resolving time correction for a geiger pulse dt_us
series. It uses intervsals built by hand and the provided background reference recording."""

import proton
import csv
from pathlib import Path
import pytest
from proton.Hardware.Detectors.geiger_pulses.deadtime import correct, split_artifacts

BACKGROUND_CSV = Path(proton.__file__).resolve().parent / "default_data" / "geiger_pulses" / "background_room.csv"

def _read_dt_us(path):
    """Pulls just the dt_us column out of a recorded pulse csv"""
    with path.open(newline = "") as f:
        return [int(row["dt_us"]) for row in csv.DictReader(f)]


class TestSplitArtifacts:
    """Tests for the ratio between real intervals and sub dead time artifacts (when a single particle is counted by the detector twice)"""

    def test_below_dead_time_is_an_artifact(self):
        """A 150us gap is under the j305's 180us dead time, so it lands in artifacts not real"""
        real, artifacts = split_artifacts([150, 2000], tube = "j305")
        assert real == [2000]
        assert artifacts == [150]

    def test_unknown_tube_raises(self):
        """A tube name outside DEAD_TIME_US has no dead time to "cut" against, so this has to be reported"""
        with pytest.raises(ValueError):
            split_artifacts([1000], tube = "not_a_tube")


class TestCorrect:
    """Tests for the full correction, the double counts cut out plus the non paralyzable rate correction"""

    def test_known_series_counts_and_artifacts(self):
        """A hand built series with one artifact should report that split"""
        report = correct([150, 1000, 2000, 3000], tube = "j305")
        assert report.registered == 4
        assert report.artifacts == 1
        assert report.true_counts == 3

    def test_empty_after_cut_does_not_divide_by_zero(self):
        """Every interval below the dead time leaves nothing to rate correct, so this must return a
           report of all zeros rather than raising an error"""
        report = correct([50, 90, 120], tube = "j305")
        assert report.true_counts == 0
        assert report.observed_cps == 0.0
        assert report.corrected_cps == 0.0

    def test_observed_rate_matches_the_interval_spacing(self):
        """N intervals of D microseconds each should give an observed rate close to 1e6 / D"""
        d = 5000
        report = correct([d] * 200, tube = "j305")
        assert report.observed_cps == pytest.approx(1_000_000 / d, rel = 1e-9)

    def test_background_room_regression(self):
        """The bundled background recording is a real data, not synthetic data, so the number of errors
           is already known: 1353 registered counts, 95 times where it double counted a particle, with the double count
          fraction is near 7%"""
        intervals = _read_dt_us(BACKGROUND_CSV)
        report = correct(intervals, tube = "j305")
        assert report.registered == 1353
        assert report.artifacts == 95
        assert report.true_counts == 1258
        assert report.artifact_fraction == pytest.approx(0.070, abs = 5e-4)
        assert report.correction_factor == pytest.approx(1.000063, abs = 1e-5)
