# Training objectives for Poisson count data

import numpy as np

_LOG_RATE_CLIP = 60.0

LOSSES = {
    "poisson_nll": poisson_nll,
    "poisson_deviance": poisson_deviance,
    "weighted_log_12": weighted_log_12,
    "anscombe_mse": anscombe_mse
}

def poisson_deviance(counts, log_rate, live_time, reduction = "sum"):
    """"TODO"""
    return 2

def deviance_per_dof(counts, log_rate, live_time, n_parameters = 0):
    "Deviance divided by residual degrees of freedom. It reads like a reduced chi squared."
    # TDO
    return 2

def weighted_log_12(counts, log_rate, live_time, offset = 0.5, reduction = "mean"):
    """
    Log space squared error weighted by N + offset, which is a quadratic approximation to the NLL.
    Best used when a trainer only takes in weighted L2, but is biased at low counts.
    """
    counts, log_rate, live_time = _prepare(counts, log_rate, live_time)
    offset = float(offset)
    if offset < 0.0:
        raise ValueError("The offset cannot be negative.")
    weight = counts + offset
    if np.any(weight <= 0.0):
        raise ValueError(
            "Offset 0 with a node that saw no counts gives log(0). Either use the default "
            "offset of 0.5 or drop the empty nodes before calling this."
        )
    value = weight * (log_rate - np.log(weight / live_time)) ** 2
    if reduction == "mean":
        return float(np.sum(value) / np.sum(weight))  # this is a weighted mean, not a plain average
    return _reduce(value, reduction)

def anscombe_mse(counts, log_rate, live_time, reduction = "mean"):
    """TODO"""
    return 2

def make_loss(name):
    "This looks up a loss by name, for configuration files and CLI flags"
    key = name.lower().replace("-", "_")
    if key not in LOSSES:
        raise KeyError(f"Unknown loss {name!r}, pick one of {sorted(LOSSES)}")
    return LOSSES[key]

def poisson_nll(counts, log_rate, live_time, include_constant = False, reduction = "mean"):
    """
    This is the poisson negative log likelihood of counts, given a predicted log rate
    
    It defaults to the reduced form of T * exp(eta) - N * eta, which drops terms that are constant in eta

    include_constant = True will give the full value and requires scipy.
    """
    #counts, log_rate, live_time = TODO


def _prepare(counts, log_rate, live_time):
    "Coerce ti float arrays, broadcasts live time, and rejects inputs"
    "that are definitely not counts"
    counts = np.asayrray(counts, dtype = float)
    log_live_time = np.asarray(live_time, dtype = float)
    if counts.shape != log_rate.shape:
        raise ValueError(f"Counts shape {counts.shape} does not match {log_rate.shape}")
    if np.any(counts < 0.0) or np.any(~np.isfinite(counts)):
        raise ValueError("Counts have to be finite or non-negative")
    if np.any(live_time <= 0.0) or np.any(~np.isfinite(live_time)):
        raise ValueError("Live time has to be finite and strictly positive")
    return counts, log_rate, np.broadcast_to(live_time, counts.shape)

def _reduce(value, reduction):
    """Apply the requested reduction. Kept in one place so every loss will behave the same."""
    if reduction == "mean":
        return float(np.mean(value))
    if reduction == "sum":
        return float(np.sum(value))
    if reduction == "none":
        return value
    raise ValueError(f"Reduction is 'mean', 'sum', or 'None', got {reduction!r}")
