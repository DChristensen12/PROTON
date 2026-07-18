"""Custom style made by a user who is using PROTON.
    This is meant to be an easier way to create a style and integrate it into PROTON
"""

# I'll add doc strings later.

import json
import re
from pathlib import Path
from proton.common.exceptions import ProtonError
from proton.Visualizations.palettes import Palette, PALETTES
from proton.Visualizations.geometry import GEOMETRIES
from proton.Visualizations import themes, style

_BUILTIN_PALETTES = frozenset(PALETTES)
_BUILTIN_MODES = frozenset(themes.MODES)
_BUILTIN_GEOMETRIES = frozenset(GEOMETRIES)
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

LOOKS = {} # name -> (geometry, palette, mode), a saved answer to use()


def _check_hex(value, where):
    """One hex, checked here so that a typo fails at register time and not mid render"""
    if not isinstance(value, str) or not _HEX.match(value):
        raise ProtonError(where + " needs a #RRGGBB hex, got " + repr(value))
    return value.upper()


def _check_name(name, registry, builtins, kind):
    """Names must be new or your own, the builtins stay what the docs say they are"""
    if not isinstance(name, str) or not name:
        raise ProtonError("a " + kind + " needs a nonempty string name")
    if name in builtins:
        raise ProtonError(name + " is a builtin " + kind + ", pick another name")
    return name


def palette(name, primary, cycle, cmap = "viridis"):
    """A palette from scratch."""
    _check_name(name, PALETTES, _BUILTIN_PALETTES, "palette")
    cycle = tuple(_check_hex(c, name + " cycle") for c in cycle)
    if not cycle:
        raise ProtonError(name + " needs at least one color in its cycle")
    if not isinstance(cmap, str):
        cmap = tuple(_check_hex(c, name + " cmap") for c in cmap)
    pal = Palette(name = name, primary = _check_hex(primary, name + " primary"),
                  cycle = cycle, cmap = cmap)
    PALETTES[name] = pal
    return pal


def derive(base, name, primary = None, cycle = None, add = None, cmap = None):
    if base not in PALETTES:
        raise ProtonError("no palette named " + str(base) + " to derive from")
    if cycle is not None and add is not None:
        raise ProtonError("pass cycle or add, not both, one replaces and the other appends")
    src = PALETTES[base]
    new_cycle = src.cycle if cycle is None else tuple(cycle)
    if add is not None:
        new_cycle = new_cycle + tuple(add)
    return palette(name,
                   primary = primary if primary is not None else src.primary,
                   cycle = new_cycle,
                   cmap = cmap if cmap is not None else src.cmap)


def stack(name, *bases, primary = None, cmap = None):
    if len(bases) < 2:
        raise ProtonError("stack needs at least two palettes")
    for b in bases:
        if b not in PALETTES:
            raise ProtonError("no palette named " + str(b) + " to stack")
    merged = []
    for b in bases:
        merged.extend(PALETTES[b].cycle)
    merged = tuple(dict.fromkeys(merged)) # order preserving dedupe, O(n)
    first = PALETTES[bases[0]]
    return palette(name,
                   primary = primary if primary is not None else first.primary,
                   cycle = merged,
                   cmap = cmap if cmap is not None else first.cmap)


def mode(name, background, foreground, muted, grid):
    _check_name(name, themes.MODES, _BUILTIN_MODES, "mode")
    world = {k: _check_hex(v, name + " " + k)
             for k, v in (("background", background), ("foreground", foreground),
                          ("muted", muted), ("grid", grid))}
    themes.MODES[name] = world
    return world


def geometry(name, cls):
    _check_name(name, GEOMETRIES, _BUILTIN_GEOMETRIES, "geometry")
    missing = [m for m in ("axes", "line", "scatter", "bar") if not callable(getattr(cls, m, None))]
    if missing:
        raise ProtonError(name + " is missing " + ", ".join(missing) + ", a geometry needs all four")
    GEOMETRIES[name] = cls
    return cls


def look(name, geometry = "formal", palette = "formal", mode = "light"):
    for value, registry, kind in ((geometry, GEOMETRIES, "geometry"),
                                  (palette, PALETTES, "palette"),
                                  (mode, themes.MODES, "mode")):
        if value not in registry:
            raise ProtonError("no " + kind + " named " + str(value))
    LOOKS[name] = (geometry, palette, mode)
    return LOOKS[name]


def apply(name):
    if name not in LOOKS:
        have = ", ".join(sorted(LOOKS)) if LOOKS else "none registered yet"
        raise ProtonError("no look named " + str(name) + ", have: " + have)
    g, p, m = LOOKS[name]
    style.use(geometry = g, palette = p, mode = m)


DEFAULT_PATH = Path.home() / ".proton" / "styles.json"


def save(path = None):
    path = Path(path) if path is not None else DEFAULT_PATH
    payload = {
        "palettes": {n: {"primary": p.primary, "cycle": list(p.cycle),
                         "cmap": p.cmap if isinstance(p.cmap, str) else list(p.cmap)}
                     for n, p in PALETTES.items() if n not in _BUILTIN_PALETTES},
        "modes": {n: themes.MODES[n] for n in themes.MODES if n not in _BUILTIN_MODES},
        "looks": {n: list(v) for n, v in LOOKS.items()},
    }
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text(json.dumps(payload, indent = 2))
    return path


def load(path = None):
    path = Path(path) if path is not None else DEFAULT_PATH
    if not path.exists():
        raise ProtonError("no styles file at " + str(path) + ", save() writes one")
    payload = json.loads(path.read_text())
    brought = []
    for n, d in payload.get("palettes", {}).items():
        PALETTES.pop(n, None) # loading your own file wins over the same names in memory
        cmap = d["cmap"] if isinstance(d["cmap"], str) else tuple(d["cmap"])
        palette(n, d["primary"], d["cycle"], cmap)
        brought.append(n)
    for n, d in payload.get("modes", {}).items():
        themes.MODES.pop(n, None)
        mode(n, **d)
        brought.append(n)
    for n, triple in payload.get("looks", {}).items():
        look(n, *triple)
        brought.append(n)
    return brought
