# for hex data only: PROTON, okabe_ito, tol_bright, tol_muted, viridis-based, etc)

"""
To be specific, this file includes hex data specifying these types of color palettes:
   - Custom Color palettes (PROTON, Soft Serenity, etc)
   - Color Blind Color palettes (protanopial, deuteranopia, tritanopia, and achromatopsia)
"""

# Always open to adding more color themes at request! 

from typing import NamedTuple
 
class Palette(NamedTuple):
    """One named color scheme"""
    name: str    # name of the color palette
    primary: str # the single series and accent color
    cycle: tuple # categorical colors, in the order the plots hand them out
    cmap: str    # matplotlib colormap name for continuous data
 
 
# Core Proton Color Palette  
PROTON = Palette(
    name = "proton",
    primary = "#75BBE7",
    cycle = ("#75BBE7", "#E77582", "#E7DA75", "#A175E7", "#75E7A1", "#E775D7"),     # hue rotations that look nice with the primary PROTON color
    cmap = "proton"
)

# Special made custom color theme 
SOFT_SERENITY = Palette(
    name = "soft_serenity",
    primary = "#99CCFF",
    cycle = ("#99CCFF", "#FF8066", "#800080"),
    cmap = ("#2B1B3D", "#800080", "#FF8066", "#99CCFF")
)
 
# Also special made custom color theme, just with additional colors in case the soft_serenity color palette requires more colors for visualizations.
SOFT_SERENITY_WIDE = Palette(
    name = "soft_serenity_wide",
    primary = "#99CCFF",
    cycle = ("#99CCFF", "#FF8066", "#800080", "#66C2A5", "#FFD966", "#5A7BA6"),
    cmap = ("#2B1B3D", "#800080", "#FF8066", "#99CCFF")
)

FORMAL = Palette(
    name = "formal",
    primary = "#0072B2",
    cycle = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#56B4E9", "#E69F00"), # A more formal color schemes for formal purposes like professional presentations or research
    cmap = "viridis"
)
 
OKABE_ITO = Palette(
    name = "okabe_ito",
    primary = "#0072B2",
     # this is the CUD eight, for color vision blindness.
    cycle = ("#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#000000"),
    cmap = "viridis"
)
 
TOL_BRIGHT = Palette(
    name = "tol_bright",
    primary = "#4477AA",
    cycle = ("#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"), # Paul Tol's bright qualitative scheme, built for contrast on white and light grey
    cmap = "viridis"
)
 
TOL_MUTED = Palette(
    name = "tol_muted",
    primary = "#332288",
    cycle = ("#332288", "#88CCEE", "#44AA99", "#117733", "#999933", "#DDCC77", "#CC6677", "#882255", "#AA4499"), # Tol's muted scheme, nine colorblind safe categories 
    cmap = "cividis"
)


BEACON = Palette(
    name = "beacon",
    primary = "#0072B2",
    # built for protanopia, the red blind form (covers protanomaly, the milder version, too)
    cycle = ("#0072B2", "#E69F00", "#74E7C4", "#B62020", "#3C3CDD", "#74C4E7"),
    cmap = "cividis"
)
 
COMPASS = Palette(
    name = "compass",
    primary = "#0072B2",
    # built for deuteranopia, the green blind form (covers deuteranomaly too)
    cycle = ("#0072B2", "#E69F00", "#74E7B9", "#A63030", "#3C3CDD", "#B6207A"),
    cmap = "cividis"
)
 
MERIDIAN = Palette(
    name = "meridian",
    primary = "#D55E00",
    # built for tritanopia, the blue blind form (covers tritanomaly too).
    cycle = ("#D55E00", "#0072B2", "#E7D074", "#8920B6", "#74E7E7", "#E774DB"),
    cmap = "viridis"
)
 
HALO_LIGHT = Palette(
    name = "halo_light",
    primary = "#011520",
    # built for achromatopsia
    cycle = ("#011520", "#551000", "#034D25", "#7B488A", "#8C7528", "#1BA3A7"),
    cmap = "gray"
)
 
HALO_DARK = Palette(
    name = "halo_dark",
    primary = "#A9FCFE",
    # halo_light for a dark background instead, built for achromatopsia
    cycle = ("#0E6A91", "#BD644E", "#56A96F", "#D99FE8", "#ECCE7D", "#A9FCFE"),
    cmap = "gray"
)
 
OGRE = Palette(
    name = "ogre",
    primary = "#7A9244",
    cycle = ("#7A9244", "#C4D300", "#5C452D", "#C3BC95"),
    cmap = ("#2A1F12", "#5C452D", "#7A9244", "#C4D300")
)
 
INVINCIBLE = Palette(
    name = "invincible",
    primary = "#00BCF0",
    cycle = ("#00BCF0", "#FFE556", "#C8412D", "#303539", "#E1EBED"),
    cmap = ("#101215", "#303539", "#00BCF0", "#FFE556")
)
 
GREEN_HILL = Palette(
    name = "green_hill",
    primary = "#2BB800",
    cycle = ("#2BB800", "#0F81D8", "#B65B00", "#DA2528", "#FFD78F", "#124F00"),
    cmap = ("#124F00", "#2BB800", "#FFD78F", "#0F81D8")
)


PALETTES = {p.name: p for p in (PROTON, SOFT_SERENITY, SOFT_SERENITY_WIDE, FORMAL, OKABE_ITO, TOL_BRIGHT, TOL_MUTED, BEACON, COMPASS, MERIDIAN, HALO_LIGHT, HALO_DARK, OGRE, INVINCIBLE, GREEN_HILL)}
 

# The following below is just so that one could easily figure out which color themes were tailored to what types of color blindness! 
# Other than the colors, the visualizations themselves are made with color blindness in mind as well

ACCESSIBLE = ("okabe_ito", "tol_bright", "tol_muted", "beacon", "compass", "meridian", "halo_light", "halo_dark")
 
# This is what each of the condition specific palettes is built for
CONDITIONS = {
    "beacon": "protanopia (and protanomaly)",
    "compass": "deuteranopia (and deuteranomaly), the most common form",
    "meridian": "tritanopia (and tritanomaly)",
    "halo_light": "achromatopsia, on a light background",
    "halo_dark": "achromatopsia, on a dark background",
}
 