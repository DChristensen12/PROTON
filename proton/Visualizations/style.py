# This will contain the use (geometry, palette, mode), as one entry point
"""
This defines the styles, which contain the geometry, palette, and mode!

Geometry pertains to the 3D or 2D looks of specific styles (for example, PROTON geometry is 3D and Formal geometry is 2D)
Palette pertains to the specific colors relating to that style, like how PROTON has its primary color and other nice colors that can be used in plots with it
Mode pertains to the background and foregrounds, like a light and dark mode

Regarding the main functions in style.py:

use() picks one value on each of the three axes,
geometry, palette, and mode, and everything downstream reads the composed result back through
current(). So it is three orthogonal arguments instead of one style file per combination (easier to use all together)!

"""

import matplotlib as mpl
from proton.common.exceptions import ProtonError
from proton.Visualizations.geometry import GEOMETRIES
from proton.Visualizations.palettes import PALETTES
from proton.Visualizations import themes

_active = {"geometry": None, "palette": None, "mode": None} # When someone specifies a style to use, this is where the active toggled mode will be stored

def use(geometry = "formal", palette = "formal", mode = "light"):
    """
    Activate a style! This will apply the composed rcParams, register the proton colormap the first
    time it is needed, and then it'll store the choice for current() to return to plots."""
    if geometry not in GEOMETRIES:
        raise ProtonError("no geometry named " + str(geometry) + ", have: " + ", ".join(GEOMETRIES))
    if palette not in PALETTES:
        raise ProtonError("no palette named " + str(palette) + ", have: " + ", ".join(PALETTES))
    if mode not in themes.MODES:
        raise ProtonError("no mode named " + str(mode) + ", have: " + ", ".join(themes.MODES))
    pal = PALETTES[palette]
    if not isinstance(pal.cmap, str):
        _register_cmap(pal)
    mpl.rcParams.update(themes.compose(pal, mode))
    _active.update(geometry = GEOMETRIES[geometry](), palette = pal, mode = mode)
 
 
def current():
    """
    This is the active (geometry, palette, mode) triple, activating the defaults on first call so a
    plot never has an error regardless of if use() was called yet."""
    if _active["geometry"] is None:
        use()
    return _active["geometry"], _active["palette"], _active["mode"]
 
 
def colors(n):
    """ This function returns n colors off the active palette, in cycle order.

    It will raise rather than wrapping around the color palette. A palette is as long as its theme really is, so running it
    past the end is a sign that a different palette is needed, not a repeat color. """
    _, pal, _ = current()
    if n > len(pal.cycle):
        wide = [p.name for p in PALETTES.values() if len(p.cycle) >= n]
        raise ProtonError(
            "the " + pal.name + " palette carries " + str(len(pal.cycle)) + " colors, but " +
            str(n) + " were requested. Palettes that reach: " + ", ".join(sorted(wide)))
    return list(pal.cycle[:n])
 
 
def _register_cmap(pal):
    """This will build a palette's own colormap from its hex ramp and registers it under the palette
    name. It will only run for palettes that carry a tuple rather than a builtin name, and only once."""
    import warnings
    from matplotlib.colors import LinearSegmentedColormap
    with warnings.catch_warnings():
        warnings.simplefilter("ignore") # the overwrite is deliberate, matplotlib warning  can be ignored
        mpl.colormaps.register(LinearSegmentedColormap.from_list(pal.name, list(pal.cmap)), force = True)
