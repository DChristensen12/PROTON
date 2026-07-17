# A specific place for composing palette + mode + rcParams 

"""A mode is the background and foreground a palette gets applied onto,
so dark and light are two small overlays that work with any palette rather than something that is
respecified per palette. compose() turns palette + mode into one rcParams dict."""

MODES = {
    "dark": {
        "background": "#0B0F14", 
        "foreground": "#EAF6FF",
        "muted": "#8FA8BA", # tick labels and axis labels
        "grid": "#1A2632"
    },
    "light": {
        "background": "#FFFFFF",
        "foreground": "#1A2632",
        "muted": "#5A6B78",
        "grid": "#D9E1E8"
    }
}


def compose(palette, mode):
    """One rcParams dict from a palette and a mode name. Everything visual goes through here,
       so that a new theme is a data change in this file and not an edit to any plot."""
    world = MODES[mode]
    return {
        "figure.facecolor": world["background"],
        "axes.facecolor": world["background"],
        "savefig.facecolor": world["background"],
        "axes.edgecolor": world["grid"],
        "axes.labelcolor": world["muted"],
        "axes.titlecolor": world["foreground"],
        "text.color": world["foreground"],
        "xtick.color": world["muted"],
        "ytick.color": world["muted"],
        "grid.color": world["grid"],
        "grid.linewidth": 0.5,
        "axes.grid": True,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": _cycler(palette.cycle),
        "image.cmap": palette.cmap if isinstance(palette.cmap, str) else palette.name,
        "font.family": "sans-serif",
        "axes.titlesize": 12,
        "figure.dpi": 120,
        "lines.linewidth": 1.8
    }


def _cycler(colors):
    """This function is the prop cycle object matplotlib needs, but built so that importing themes stays light"""
    from cycler import cycler
    return cycler(color = list(colors))
