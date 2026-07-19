"""Dead time handling for Geiger pulse data.

A Geiger-Müller tube cannot fire twice inside its dead time, so any recorded interval shorter than that is not
a second particle. It is the front end registering one event twice, what Knoll calls a resolving
time artifact. We will remove those at the physical dead time, then correct the surviving rate for the
counts really lost while the tube was recovering.

The rate correction uses the non paralyzable model, which is the standard choice for a GM tube
(Knoll, Radiation Detection and Measurement, 4th ed., Wiley 2010; ORTEC Experiment 2, Geiger
Counting). That model is a one parameter approximation. Real GM behavior sits somewhere between the
paralyzable and non paralyzable cases and a two parameter hybrid fits better at high rates (Lee and
Gardner 2000). At background the correction here is far below a percent, so the approximation is
harmless, but I am not saying that it is exact.

Dead times: J305 is about 180 us, SBM-20 about 190 us. These are vendor figures. For a real
measurement you would find your own tube's dead time with the two source method rather than just use these values
"""

from typing import NamedTuple

DEAD_TIME_US = {"j305": 180, "sbm20": 190} # Add your own tube/exact values as needed 


class DeadTimeReport(NamedTuple):
    """What the correction did, so the removal is reported rather than missed"""

    tube: str
    dead_time_us: int
    registered: int          # every interval that came in
    artifacts: int           # intervals below the dead time, removed
    true_counts: int         # registered minus artifacts
    artifact_fraction: float # artifacts over registered, a property of this specific front end
    observed_cps: float      # true counts per second, before the rate correction
    corrected_cps: float     # after the non paralyzable correction
    correction_factor: float # corrected over observed, how much the recovery loss mattered


def split_artifacts(intervals_us, tube = "j305"):
    """Split intervals into real ones and sub dead time artifacts.

    Returns (real, artifacts) as two lists. we give back the artifacts too, since their count and
    spacing are worth looking at, not something to throw away without reporting it.
    """
    if tube not in DEAD_TIME_US:
        raise ValueError("unknown tube " + str(tube) + ", expected one of " + ", ".join(sorted(DEAD_TIME_US)))
    floor = DEAD_TIME_US[tube]
    real = [dt for dt in intervals_us if dt >= floor]
    artifacts = [dt for dt in intervals_us if dt < floor]
    return real, artifacts


def correct(intervals_us, tube = "j305"):
    """Remove resolving time artifacts, then dead time correct the surviving rate.

    intervals_us is the dt_us column from a pulse recording. Returns a DeadTimeReport. The observed
    rate comes from the real intervals only, since the artifacts were never real particles. The
    non paralyzable correction is m = n / (1 - n * tau), with n in counts per second and tau in
    seconds (ORTEC Experiment 2).
    """
    real, artifacts = split_artifacts(intervals_us, tube)
    floor = DEAD_TIME_US[tube]
    registered = len(intervals_us)

    if not real:
        # nothing survived the cut, so there is no rate to report
        return DeadTimeReport(tube, floor, registered, len(artifacts), 0, 0.0, 0.0, 0.0, 1.0)

    # each dt is the gap to the previous pulse, so the real intervals sum to the live recording time
    total_us = sum(real)
    true_counts = len(real)
    observed_cps = true_counts * 1_000_000 / total_us

    tau_s = floor / 1_000_000
    denom = 1 - observed_cps * tau_s
    # denom goes to zero as the tube saturates. at background it is basically 1, but guard anyway.
    if denom <= 0:
        raise ValueError("observed rate too high for this dead time, the non paralyzable model breaks down here")
    corrected_cps = observed_cps / denom

    return DeadTimeReport(
        tube = tube,
        dead_time_us = floor,
        registered = registered,
        artifacts = len(artifacts),
        true_counts = true_counts,
        artifact_fraction = len(artifacts) / registered,
        observed_cps = observed_cps,
        corrected_cps = corrected_cps,
        correction_factor = corrected_cps / observed_cps,
    )
