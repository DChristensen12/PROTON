# I will specify how the tables should be constructed for each style here

"""
These are custom tables make specifically for the styles they belong to. 

Proton: A 3D object as a table
Formal: A table one might expect to find in a paper.

Which table is constructed depends which style.use was picked.
"""

import numpy as np
from proton.common.exceptions import ProtonError
from proton.Visualizations import solids
from proton.Visualizations.style import current
from proton.Visualizations.geometry import shade, FormalGeometry


def table(rows, header = True, figsize = None, rules = "booktabs"):
    """
    This will Render rows (an iterable of same length tuples) as a table under the active style and
    retiurn the figure. 

    The header treats the first row as the header row.
    
    The rules argument only matters for the formal render, as booktabs 
    is the journal convention (three horizontal rules, no verticals), grid draws 
    every row and column line for long reference tables.
    """
    import matplotlib.pyplot as plt
    rows = [tuple(str(c) for c in r) for r in rows]
    if not rows:
        raise ProtonError("a table needs at least one row")
    n_cols = len(rows[0])
    if any(len(r) != n_cols for r in rows):
        raise ProtonError("every row needs the same number of cells")
    if rules not in ("booktabs", "grid"):
        raise ProtonError("rules is booktabs or grid, not " + str(rules))

    geom, pal, mode = current()
    # column widths follow the content, one table sizing rule 
    weights = np.array([max(len(r[c]) for r in rows) for c in range(n_cols)], dtype = float)
    weights = np.maximum(weights, 4)
    fractions = weights / weights.sum()
    n_body = len(rows) - (1 if header else 0)
    if figsize is None:
        figsize = (1.6 + 1.05 * weights.sum() / 8, 1.2 + 0.42 * (n_body + 1))

    fig = plt.figure(figsize = figsize)
    if isinstance(geom, FormalGeometry):
        _formal_table(fig, rows, header, fractions, pal, rules)
    else:
        _proton_table(fig, rows, header, fractions, pal)
    return fig


def _formal_table(fig, rows, header, fractions, pal, rules):
    """
    renders a table that looks like it'd be in a journal.
    """
    import matplotlib.pyplot as plt
    fg = plt.rcParams["text.color"]
    ax = fig.add_subplot()
    ax.set_axis_off()
    n = len(rows)
    edges = np.concatenate(([0], np.cumsum(fractions)))
    centers = (edges[:-1] + edges[1:]) / 2
    for i, row in enumerate(rows):
        y = 1 - (i + 0.5) / n
        bold = header and i == 0
        for cx, cell in zip(centers, row):
            ax.text(cx, y, cell, ha = "center", va = "center",
                    fontsize = 11 if bold else 10,
                    fontweight = "bold" if bold else "normal")
    if rules == "booktabs":
        ax.plot([0, 1], [1, 1], color = fg, linewidth = 1.6)         # toprule
        if header:
            ax.plot([0, 1], [1 - 1 / n] * 2, color = fg, linewidth = 0.9) # midrule
        ax.plot([0, 1], [0, 0], color = fg, linewidth = 1.6)         # bottomrule
    else:
        for i in range(n + 1): # every row line, the outer ones heavier
            lw = 1.4 if i in (0, n) or (header and i == 1) else 0.6
            ax.plot([0, 1], [1 - i / n] * 2, color = fg, linewidth = lw)
        for x in edges: # every column line
            ax.plot([x, x], [0, 1], color = fg, linewidth = 1.4 if x in (0.0, 1.0) else 0.6)
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(-0.03, 1.03)


def _proton_table(fig, rows, header, fractions, pal):
    """
    Makes the 3D rendered PROTON style table
    """
    n = len(rows)
    W, H = 10.0, 10.0 * fig.get_figheight() / fig.get_figwidth() # scene units are matched to the canvas shape
    ax = solids.front_scene(fig, spans = (W * 1.04, 2.6, H * 1.04))

    ink = "#DDEBF5"
    row_h = H * 0.86 / n
    top = H * 0.86 / 2

    solids.add_solid(ax, solids.superellipsoid((0, 0.5, 0), (W, 1.5, H), roundness = 0.16), pal.primary, zorder = 1)
    solids.add_solid(ax, solids.superellipsoid((0, -0.4, 0), (W * 0.95, 0.55, H * 0.92), roundness = 0.12),
                     "#101820", zorder = 2)

    lefts = np.concatenate(([0], np.cumsum(fractions))) * W * 0.9 - W * 0.45
    centers = (lefts[:-1] + lefts[1:]) / 2
    start = 0
    if header:
        z = top - row_h / 2
        for cx, cell in zip(centers, rows[0]):
            ax.text(cx, -1.1, z, cell, ha = "center", va = "center",
                    color = pal.primary, fontsize = 11, fontweight = "bold", zorder = 9)
        ax.plot([-W * 0.44, W * 0.44], [-0.72] * 2, [top - row_h] * 2,
                color = pal.primary, linewidth = 2.2, zorder = 8) 
        start = 1
    for i, row in enumerate(rows[start:]):
        z = top - (i + start + 0.5) * row_h
        for cx, cell in zip(centers, row):
            ax.text(cx, -1.1, z, cell, ha = "center", va = "center",
                    color = ink, fontsize = 10, zorder = 9)
        if i: # row rules sit flat on the panel, lines not solids, which keeps them nice and crisp looking
            ax.plot([-W * 0.44, W * 0.44], [-0.72] * 2, [z + row_h / 2] * 2,
                    color = shade(pal.primary, 0.7), linewidth = 1.2, zorder = 8)
