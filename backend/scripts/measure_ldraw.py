"""Measure LEGO parts by reading their LDraw geometry, instead of recalling them.

Every .dat file is a list of triangles and quads in LDU. Resolve the sub-file
references, apply the transforms, and a part's real dimensions and — for a slope —
which way it descends fall straight out of the vertex cloud. Nothing here is
remembered, guessed, or eyeballed.

Conventions, from the LDraw spec:
    1 stud = 20 LDU in X and Z; 1 brick = 24 LDU tall; 1 plate = 8.
    +Y points DOWN, so a smaller y is higher up.
    A brick's origin is the centre of its TOP face: the body spans y 0..24 and
    the studs poke up to y = -4.
"""

from __future__ import annotations

import csv
import os
import re
import sys

import numpy as np

LIB = "/private/tmp/claude-501/-Users-xinyunzhang/c96f27f5-e866-42ae-ab1a-afa0495110b6/scratchpad/ldraw-lib/ldraw"
PARTS_CSV = "/private/tmp/claude-501/-Users-xinyunzhang/c96f27f5-e866-42ae-ab1a-afa0495110b6/scratchpad/parts.csv"

STUD = 20.0
_cache: dict[str, np.ndarray] = {}


def _find(name: str) -> str | None:
    name = name.replace("\\", "/").lower()
    for rel in (f"parts/{name}", f"p/{name}", name):
        path = os.path.join(LIB, rel)
        if os.path.exists(path):
            return path
    return None


def vertices(name: str, depth: int = 0) -> np.ndarray:
    """Every surface vertex of a part, in its own coordinates.

    Surfaces only — line types 2 and 5 are edge annotations that sometimes run
    outside the solid, and including them inflates the bounding box.
    """
    key = name.lower()
    if key in _cache:
        return _cache[key]
    if depth > 12:  # cycles in the library would otherwise recurse forever
        return np.zeros((0, 3))
    path = _find(name)
    if not path:
        return np.zeros((0, 3))
    _cache[key] = np.zeros((0, 3))  # placeholder, breaks self-reference

    out: list[np.ndarray] = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            f = line.split()
            if not f:
                continue
            if f[0] == "1" and len(f) >= 15:
                try:
                    nums = [float(v) for v in f[2:14]]
                except ValueError:
                    continue
                t = np.array(nums[0:3])
                m = np.array(nums[3:12]).reshape(3, 3)
                sub = vertices(f[14], depth + 1)
                if len(sub):
                    out.append(sub @ m.T + t)
            elif f[0] in ("3", "4"):
                n = 3 if f[0] == "3" else 4
                try:
                    pts = [float(v) for v in f[2 : 2 + 3 * n]]
                except ValueError:
                    continue
                out.append(np.array(pts).reshape(n, 3))

    result = np.vstack(out) if out else np.zeros((0, 3))
    _cache[key] = result
    return result


# Anything under this is a chamfer, a groove or a rounded edge, not a shape.
# A "Tile 1 x 4 with Groove" reads as a 4 LDU step if you go any lower, and the
# whole tile table comes back classified as slopes.
FLAT_LDU = 6.0

# Three slices along an axis: the outer quarter at each end, and the middle third.
# Fixed bins were the first attempt and they were wrong — a 2-stud slope has
# vertices at three or four z values, so most bins came out empty, the profile
# went NaN, and every short slope was reported flat. Sampling where the geometry
# actually is removes the assumption that it is evenly distributed.
_END = 0.25
_MID = (0.35, 0.65)


def _slices(v: np.ndarray, axis: int) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    lo, hi = v[:, axis].min(), v[:, axis].max()
    if hi - lo < 1e-6:
        return None
    span = hi - lo
    a = v[v[:, axis] <= lo + _END * span]
    b = v[v[:, axis] >= hi - _END * span]
    m = v[(v[:, axis] >= lo + _MID[0] * span) & (v[:, axis] <= lo + _MID[1] * span)]
    if not len(a) or not len(b) or not len(m):
        return None
    return a, b, m


def stud_vertices(name: str, depth: int = 0) -> np.ndarray:
    """Every vertex belonging to a stud primitive, in this part's coordinates.

    Positional, not nominal. The first attempt asked "does this part reference a
    file called stud*?" and got tiles wrong: a tile has no studs on top but its
    underside carries anti-stud tubes, which are also stud primitives. Every tile
    in the library came back 4 LDU tall instead of 8. Where the stud geometry
    *is* answers the question; what it is called does not.
    """
    if depth > 8:
        return np.zeros((0, 3))
    path = _find(name)
    if not path:
        return np.zeros((0, 3))
    out: list[np.ndarray] = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            f = line.split()
            if len(f) < 15 or f[0] != "1":
                continue
            try:
                nums = [float(v) for v in f[2:14]]
            except ValueError:
                continue
            t = np.array(nums[0:3])
            m = np.array(nums[3:12]).reshape(3, 3)
            ref = f[14].lower().replace("\\", "/").rsplit("/", 1)[-1]
            sub = (
                vertices(f[14], depth + 1)
                if ref.startswith("stud")
                else stud_vertices(f[14], depth + 1)
            )
            if len(sub):
                out.append(sub @ m.T + t)
    return np.vstack(out) if out else np.zeros((0, 3))


def measure(part_num: str) -> dict | None:
    v = vertices(f"{part_num}.dat")
    if len(v) < 8:
        return None

    # Where the origin sits inside the part, measured — not assumed.
    #
    # There is no single convention. 3005 (Brick 1x1) runs y -4..24: the origin is
    # the centre of the top face and the body hangs below it. 54200 (Cheese Slope)
    # runs -15.6..0: the origin is the bottom and the part rises above it. Storing
    # a single "height" and inferring the rest put half the slope table at h=0.
    # Storing both extents needs no convention at all — to seat a part on a surface
    # at world Y = s, put its origin at s - yMax.
    y_min, y_max = float(v[:, 1].min()), float(v[:, 1].max())
    sv = stud_vertices(f"{part_num}.dat")
    # Studs count only when they are the highest thing on the part. Underside
    # tubes are stud primitives too, and they sit at the other end.
    studs = bool(len(sv)) and float(sv[:, 1].min()) <= y_min + 0.5
    body = v[v[:, 1] >= y_min + (4.0 if studs else 0.0) - 0.01]
    if len(body) < 8:
        body = v

    width = (v[:, 0].max() - v[:, 0].min()) / STUD
    deep = (v[:, 2].max() - v[:, 2].min()) / STUD
    height = float(body[:, 1].max() - body[:, 1].min())

    def read(axis: int) -> dict:
        s = _slices(body, axis)
        if s is None:
            return {"drop": 0.0, "dir": None, "taper": 0.0, "cut": 0.0}
        a, b, m = s
        # Top surface: smaller y is higher, because LDraw's +Y points down.
        ta, tb, tm = float(a[:, 1].min()), float(b[:, 1].min()), float(m[:, 1].min())
        # Underside: this is what an arch cuts away and what an inverted slope angles.
        ua, ub, um = float(a[:, 1].max()), float(b[:, 1].max()), float(m[:, 1].max())
        return {
            "drop": abs(tb - ta),
            "dir": ("+" if tb > ta else "-"),
            # Falls away at both ends and is highest in the middle: a cone, a dome,
            # an arch's back. Not a direction, so it must not be read as one.
            "taper": min(ta, tb) - tm,
            # Cut away underneath in the middle only: an arch.
            "cut": min(ua, ub) - um,
        }

    x, z = read(0), read(2)
    # Whichever axis carries the bigger change is the one the shape is oriented on.
    axis, other = ("x", x) if x["drop"] >= z["drop"] else ("z", z)
    sloped = other["drop"] >= FLAT_LDU
    taper = max(x["taper"], z["taper"])
    cut = max(x["cut"], z["cut"])

    return {
        "part": part_num,
        "widthStuds": round(width, 2),
        "depthStuds": round(deep, 2),
        "heightLDU": round(height, 1),
        # Both extents, so a caller can seat the part without knowing which end
        # its origin is on.
        "yMinLDU": round(y_min, 1),
        "yMaxLDU": round(y_max, 1),
        # Horizontal extents too, and for the same reason: a part is not
        # necessarily centred on its own origin. 3040b spans z -30..+10, so its
        # footprint centre is at -10. Any placement formula that assumes a part is
        # centred puts every slope one stud out, and does it silently.
        "xMinLDU": round(float(v[:, 0].min()), 1),
        "xMaxLDU": round(float(v[:, 0].max()), 1),
        "zMinLDU": round(float(v[:, 2].min()), 1),
        "zMaxLDU": round(float(v[:, 2].max()), 1),
        "hasStuds": studs,
        # The number that decides a slope's rotation, read off the vertices rather
        # than recalled: which way the top surface descends, and by how much.
        "slopeAxis": axis if sloped else None,
        "slopeDir": other["dir"] if sloped else None,
        "slopeDrop": round(other["drop"], 1) if sloped else 0.0,
        "taperLDU": round(taper, 1) if taper >= FLAT_LDU else 0.0,
        "archLDU": round(cut, 1) if cut >= FLAT_LDU else 0.0,
    }


SKIP = re.compile(
    r"(pr\d|pat\d|Sticker|Print|Duplo|Znap|Scala|Belville|Fabuland|Cloth|Minifig"
    r"|Technic|Electric|Sports|Assembly|Modified|with Axle|with Pin|with Hole"
    r"|Magnet|Wheel|Windscreen|Train|Boat|Animal|Plant)",
    re.I,
)
WANT = re.compile(
    r"^(Brick Sloped|Brick Arch|Brick Curved|Brick Round|Brick \d|Tile |Tile Round"
    r"|Plate |Plate Round|Cone |Dish |Wedge |Panel |Cylinder|Dome|Brick Special)",
    re.I,
)

if __name__ == "__main__":
    rows = list(csv.DictReader(open(PARTS_CSV)))
    cand = [
        r for r in rows
        if WANT.match(r["name"]) and not SKIP.search(r["name"]) and not SKIP.search(r["part_num"])
    ]
    print(f"candidates {len(cand)}", file=sys.stderr)

    out = []
    for r in cand:
        m = measure(r["part_num"])
        if not m:
            continue
        m["name"] = r["name"]
        out.append(m)

    w = csv.DictWriter(
        sys.stdout,
        fieldnames=["part", "name", "widthStuds", "depthStuds", "heightLDU",
                    "slopeAxis", "slopeDir", "slopeDrop", "yMinLDU", "yMaxLDU", "hasStuds"],
    )
    w.writeheader()
    for m in out:
        w.writerow(m)
    print(f"measured {len(out)} of {len(cand)}", file=sys.stderr)
