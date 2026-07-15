"""solids.py contains the mesh builders for the PROTON look, 3D object renders."""

import numpy as np
from matplotlib.colors import LightSource

LIGHT = LightSource(azdeg = 255, altdeg = 30) # This is mostly front facing with up left tilt. 

def _p(w, e):
    """This is the signed power that shaped the superellipsoid, so
    the sign is kept so that the surface closes"""
    return np.sign(w) * np.abs(w) ** e

def superellipsoid(center, size, roundness = 0.22, nu = 48, nv = 48):
    """
    This is just one rounded solid with the size of the full (x, y, z) extent.
    The roundness slides the corners.
    It'll return the X, Y, Z surface grids.
    """
    cx, cy, cz = center
    ax_, ay, az = (s / 2 for s in size)
    u = np.linspace(-np.pi / 2, np.pi / 2, nu)
    v = np.linspace(-np.pi, np.pi, nv)
    U, V = np.meshgrid(u, v)
    X = cx + ax_ * _p(np.cos(U), roundness) * _p(np.cos(V), roundness)
    Y = cy + ay * _p(np.cos(U), roundness) * _p(np.sin(V), roundness)
    Z = cz + az * _p(np.sin(U), roundness)
    return X, Y, Z



