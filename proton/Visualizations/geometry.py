# A place to insert the geometry I'll use for the visualizations.
"""FlatGeometry and SolidGeometry, this is the mark-drawing interface"""

import colorsys
import numpy as np
from matplotlib.patches import Polygon, Ellipse

def shade(hexcolor, factor):
    """
    This is the lighting model, so a lightness shift on a hex.
    factor being above 1 would move hex towards white and below 1 to black.
    """
    r, g, b = (int(hexcolor.lstrip("#")[i: i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(0.0, min(1.0, 1 * factor))
    r, g, b, = colorsys.hls_to_rgb(h, l, s)
    return (r, g, b)

class PROTONGeometry:
    """This is renderer for the PROTON style."""
    DEPTH = 0.32 # this is the extrusion offset as a fraction of bar width
 
    def line(self, ax, x, y, color, **kwargs):
        """A tube read: a dark casing, the body, and a bright core stacked on one path"""
        lw = kwargs.pop("linewidth", 3.4)
        caps = dict(solid_capstyle = "round", solid_joinstyle = "round")
        artists = []
        artists += ax.plot(x, y, color = shade(color, 0.45), linewidth = lw * 1.9, zorder = 2.0, **caps)
        artists += ax.plot(x, y, color = color, linewidth = lw * 1.15, zorder = 2.1, **caps)
        artists += ax.plot(x, y, color = shade(color, 1.55), linewidth = lw * 0.4,
                           alpha = 0.9, zorder = 2.2, **caps, **kwargs)
        return artists
 
    def scatter(self, ax, x, y, color, size = 140, **kwargs):
        """Lit spheres: a body circle, a darker lower limb, and a small highlight up and left."""
        artists = []
        artists.append(ax.scatter(x, y, s = size * 1.12, color = shade(color, 0.5), zorder = 3.0, **kwargs))
        artists.append(ax.scatter(x, y, s = size, color = color, zorder = 3.1))
        # the highlight rides up and left of center by a fraction of the marker radius
        r_pts = np.sqrt(size) / 2
        offset = r_pts * 0.38
        artists.append(ax.scatter(x, y, s = size * 0.16, color = shade(color, 1.7),
                                  alpha = 0.95, zorder = 3.2,
                                  transform = _nudged(ax, -offset * 0.7, offset)))
        return artists
 
    def bar(self, ax, x, height, color, width = 0.7, **kwargs):
        """Extruded blocks: the front face in the base color, the top catching the light, and
        the right side falling into shadow. Corners are computed per bar, so any number of bars
        works."""
        x = np.atleast_1d(np.asarray(x, dtype = float))
        height = np.atleast_1d(np.asarray(height, dtype = float))
        dx = width * self.DEPTH
        dy_scale = self._depth_rise(ax, height)
        artists = []
        for cx, h in zip(x, height):
            left, right = cx - width / 2, cx + width / 2
            dy = dy_scale
            front = [(left, 0), (right, 0), (right, h), (left, h)]
            top = [(left, h), (right, h), (right + dx, h + dy), (left + dx, h + dy)]
            side = [(right, 0), (right + dx, dy), (right + dx, h + dy), (right, h)]
            for face, factor, z in ((side, 0.55, 2.0), (top, 1.35, 2.1), (front, 1.0, 2.2)):
                artists.append(ax.add_patch(Polygon(face, closed = True,
                                                    facecolor = shade(color, factor),
                                                    edgecolor = shade(color, 0.4),
                                                    linewidth = 0.6, zorder = z, **kwargs)))
        # the patches do not autoscale on their own the way bar() does, so we shall stretch the view by hand
        ax.update_datalim([(x.min() - width, 0), (x.max() + width + dx, height.max() + dy_scale * 2)])
        ax.autoscale_view()
        return artists
 
    def _depth_rise(self, ax, height):
        """The vertical part of the extrusion in data units, kept proportional to the data span
        so tall and short charts extrude by the same visual amount."""
        span = float(np.max(height)) if np.size(height) else 1.0
        return (span if span > 0 else 1.0) * self.DEPTH * 0.12
 

class FormalGeometry:
    """The renderer for the formal style."""
 
    def line(self, ax, x, y, color, **kwargs):
        """A plain line"""
        return ax.plot(x, y, color = color, **kwargs)
 
    def scatter(self, ax, x, y, color, size = 36, **kwargs):
        """Plain dots"""
        return ax.scatter(x, y, color = color, s = size, **kwargs)
 
    def bar(self, ax, x, height, color, width = 0.7, **kwargs):
        """Plain bars"""
        return ax.bar(x, height, color = color, width = width, **kwargs)
 

def _nudged(ax, dx_pts, dy_pts):
    """A transform offset by a few points, how the sphere highlight sits off center"""
    from matplotlib.transforms import ScaledTranslation
    return ax.transData + ScaledTranslation(dx_pts / 72, dy_pts / 72, ax.figure.dpi_scale_trans)
 
 
GEOMETRIES = {"proton": PROTONGeometry, "formal": FormalGeometry}
