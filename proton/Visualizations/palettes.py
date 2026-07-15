# for hex data only: PROTON, okabe_ito, tol_bright, tol_muted, viridis-based, etc)

from typing import NamedTuple
 
class Palette(NamedTuple):
    """One named color scheme"""
    name: str    # name of the color palette
    primary: str # the single series and accent color
    cycle: tuple # categorical colors, in the order the plots hand them out
    cmap: str    # matplotlib colormap name for continuous data
 
 
PROTON = Palette(
    name = "proton",
    primary = "#75BBE7",
    cycle = ("#75BBE7", "#E77582", "#E7DA75", "#A175E7", "#75E7A1", "#E775D7"),     # hue rotations that look nice with the primary PROTON color
    cmap = "proton", 
)
 
FORMAL = Palette(
    name = "formal",
    primary = "#0072B2",
    cycle = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#56B4E9", "#E69F00"), # Intended for formal uses of PROTON
    cmap = "viridis",
)
 
OKABE_ITO = Palette(
    name = "okabe_ito",
    primary = "#0072B2",
     # this is the CUD eight, to cover color vision blindness.
    cycle = ("#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#000000"),
    cmap = "viridis",
)
 
TOL_BRIGHT = Palette(
    name = "tol_bright",
    primary = "#4477AA",
    cycle = ("#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"), # Paul Tol's bright qualitative scheme, built for contrast on white and light grey
    cmap = "viridis",
)
 
TOL_MUTED = Palette(
    name = "tol_muted",
    primary = "#332288",
    cycle = ("#332288", "#88CCEE", "#44AA99", "#117733", "#999933", "#DDCC77", "#CC6677", "#882255", "#AA4499"), # Tol's muted scheme, nine colorblind safe categories when bright runs out
    cmap = "cividis",
)

# I will add more color palettes.
 
PALETTES = {p.name: p for p in (PROTON, FORMAL, OKABE_ITO, TOL_BRIGHT, TOL_MUTED)}
