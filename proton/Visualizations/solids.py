"""
solids.py contains the mesh builders for the PROTON look, 3D object renders.
Essentially, this is just a way for me to make a custom table for PROTON, if the PROTON
style is chosen.
"""

import numpy as np
from matplotlib.colors import LightSource

LIGHT = LightSource(azdeg = 255, altdeg = 30) # This is mostly front facing with up left tilt. 


def add_solid(ax, mesh, color, zorder):
    """This puts one lit mesh into the scene. The scene then runs with the computed z order off
    and paints back to front, where front facing objects are layered so the painter's order just happens
    to work."""
    X, Y, Z = mesh
    return ax.plot_surface(X, Y, Z, color = color, shade = True, lightsource = LIGHT,
                           linewidth = 0, antialiased = True, zorder = zorder)


def front_scene(fig, spans = (12.0, 2.6, 8.0)):
    """This is the creation of the custom table for PROTON itself. It is front facing."""
    ax = fig.add_subplot(projection = "3d")
    ax.set_proj_type("ortho")
    ax.view_init(elev = 0, azim = -90)
    ax.set_axis_off()
    ax.computed_zorder = False # painter's order, back to front, is a specified route for stacked slabs
    sx, sy, sz = spans
    ax.set_xlim(-sx / 2, sx / 2)
    ax.set_ylim(-sy / 2, sy / 2)
    ax.set_zlim(-sz / 2, sz / 2)
    ax.set_box_aspect(spans, zoom = 1.05)
    fw, fh = fig.get_size_inches()
    k = 0.88 * max(fw, fh)
    # the projection lands a fixed fraction of the viewport square up and to the right of the
    # rect center, which is measured at 0.0136 of the square side across canvas shapes, so the rect
    # shifts down left by the same amount and the object comes out centered when we account for this
    off = 0.0136 * k
    ax.set_position([(1 - k / fw) / 2 - off / fw, (1 - k / fh) / 2 - off / fh, k / fw, k / fh])
    return ax

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

def sphere(center, r, n = 28):
    """Makes a sphere."""
    return superellipsoid(center, (2 * r, 2 * r, 2 * r), roundness = 1.0, nu = n, nv = n)

def cylinder(center, r, length, axis = "z", n = 36, roundness = 0.35):
    """Makes a cylinder"""
    size = {"x": (length, 2 * r, 2 * r), "y": (2 * r, length, 2 * r), "z": (2 * r, 2 * r, length)}[axis]
    return superellipsoid(center, size, roundness = roundness, nu = n, nv = n)
