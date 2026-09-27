"""
Discretization invariance checks for models that maps a grid to another grid
"""

from dataclasses import dataclass
import numpy as np

def resample_spectral(field, shape, axes = None):
    """Resamples a periodic field by zero padding or truncating its spectrum"""
    