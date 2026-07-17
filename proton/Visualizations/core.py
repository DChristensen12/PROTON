# This will contain the figure lifecycle plus the static/animation seam

from pathlib import Path
import matplotlib.pyplot as plt
from proton.common.exceptions import ProtonError
from proton.Visualizations.style import current
 
 
def figure(figsize = (7.0, 4.4)):
    """
    This is one styled figure and axes. The rcParams from style.use define the look, this just makes
    sure current() ran so the defaults are in place before anything draws."""
    current()
    return plt.subplots(figsize = figsize)
 
 
def save(fig, path):
    """save writes a figure out, making the folder on the way, and close it so long scripts do not
    pile up open figures."""
    path = Path(path)
    path.parent.mkdir(parents = True, exist_ok = True)
    fig.savefig(path, bbox_inches = "tight")
    plt.close(fig)
    return path
 
 
def animate(fig, draw_frame, frames, path, fps = 20):
    """animate turns a per frame draw function into a file. draw_frame takes the frame index and mutates
    the artists, gif goes through pillow and mp4 through ffmpeg, picked off the extension."""
    from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter
    path = Path(path)
    path.parent.mkdir(parents = True, exist_ok = True)
    suffix = path.suffix.lower()
    if suffix == ".gif":
        writer = PillowWriter(fps = fps)
    elif suffix == ".mp4":
        writer = FFMpegWriter(fps = fps)
    else:
        raise ProtonError("animate writes .gif or .mp4, not " + suffix)
    anim = FuncAnimation(fig, draw_frame, frames = frames)
    anim.save(path, writer = writer)
    plt.close(fig)
    return path
