"""
This is the __init__.py gor PROTON's visualization layer.
use() picks the look, figure(), save() and animate() are the
mechanics, and the plot modules build on both."""

from proton.Visualizations.style import use, current
from proton.Visualizations.core import figure, save, animate
from proton.Visualizations.palettes import PALETTES

__all__ = ["use", "current", "figure", "save", "animate", "PALETTES"]
