"""Regenerate app/services/lego_shapes.py from the LDraw and Rebrickable data.

Run this instead of editing lego_shapes.py, and instead of adding a part from
memory. Every number in the generated file is measured or counted:

    identity     Rebrickable parts.csv — the name is the only reliable statement
                 of what a part *is*. Geometry cannot recover intent: an ordinary
                 brick is hollow underneath, which to a purely geometric test
                 looks exactly like an arch, and did.
    geometry     the official LDraw library — size, height, where the origin sits
                 inside the part, and which way a slope descends. This is the
                 same geometry the browser viewer renders, so a part that
                 measures 2 studs wide here is 2 studs wide on screen.
    commonness   Rebrickable inventory_parts.csv — how many set inventories the
                 part appears in. Without this the library fills with parts that
                 exist but that nobody can source, and the generated shopping
                 list stops being something you could order.

Inputs, none of which are committed (they are 150 MB together):

    LDRAW_DIR    unpacked https://library.ldraw.org/library/updates/complete.zip
    REBRICKABLE  a directory holding parts.csv and inventory_parts.csv from
                 https://rebrickable.com/downloads/

    python scripts/build_shape_library.py --ldraw ~/ldraw --data ~/rebrickable
"""

from __future__ import annotations

import argparse
import collections
import csv
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Appearing in fewer sets than this, a part is a curiosity. The first pass set it
# at 150 on the reasoning that asking a builder to source forty of a rare part is
# asking them not to build the model — which held while the only way to get a
# part was to buy it, and stopped holding when the answer became "print it". A
# shape that appeared in five sets is a shape LEGO designed, moulded and shipped;
# that is a good enough warrant to build with. Override with --min-sets.
DEFAULT_MIN_SETS = 5

# The name patterns that define each family, in the order the generator prefers
# to reach for them.
FAMILIES: list[tuple[str, str]] = [
    ("brick", r"^Brick \d+ x \d+$"),
    ("plate", r"^Plate \d+ x \d+$"),
    ("tile", r"^Tile \d+ x \d+(?: with Groove)?$"),
    ("slope", r"^Brick Sloped \d+° \d+ x \d+"),
    ("slope_inverted", r"^Brick Sloped Inverted \d+° \d+ x \d+"),
    ("arch", r"^Brick Arch \d+ x \d+"),
    ("curved", r"^Brick Curved \d+ x \d+"),
    ("round_brick", r"^Brick Round \d+ x \d+"),
    ("round_plate", r"^Plate Round \d+ x \d+"),
    ("round_tile", r"^Tile Round \d+ x \d+"),
    ("cone", r"^Cone \d+ x \d+"),
    ("dish", r"^Dish \d+ x \d+"),
    ("dome", r"^Dome \d+ x \d+"),
    ("cylinder", r"^Cylinder \d+ x \d+"),
    ("wedge", r"^Wedge \d+ x \d+"),
    ("wedge_plate", r"^Wedge Plate \d+ x \d+"),
    ("panel", r"^Panel \d+ x \d+ x \d+"),
    # Added when the brief changed from "a list you can order" to "a list you
    # can order or print". These are the families a building actually wants and
    # the first pass had no pattern for, so they were skipped without ever being
    # counted as dropped.
    ("window", r"^Window \d+ x \d+"),
    ("door", r"^Door \d+ x \d+"),
    ("wedge_curved", r"^Brick Wedged, Curved"),
    ("wedge_sloped", r"^Brick Wedged, Sloped"),
    ("curved_inverted", r"^Brick Curved Inverted \d+ x \d+"),
    ("round_corner", r"^Brick Round Corner \d+ x \d+"),
    # Studs facing sideways. This is the whole SNOT vocabulary — the technique
    # that lets a facade carry detail finer than a stud, and the reason a real
    # Architecture set does not read as a staircase.
    ("brick_modified", r"^Brick Special \d+ x \d+"),
    ("plate_modified", r"^Plate Special \d+ x \d+"),
    ("bracket", r"^Bracket \d+ x \d+"),
    # Big curved shells. Nothing else in the library can make the roof of an
    # opera house.
    ("shell", r"^Aircraft Fuselage"),
]

# Variants that are the same shape with extra engineering. They change what the
# part connects to, never what it looks like from the front, and keeping them
# would put four indistinguishable rows in one shopping list.
SKIP = re.compile(
    r"(pr\d|pat\d|p\d\d|Sticker|Print|Duplo|Znap|Scala|Belville|Fabuland|Cloth"
    r"|Minifig|Technic|Electric|Sports|Assembly|Magnet|Wheel|Windscreen|Train"
    r"|Boat|Animal|Plant|with Axle|with Pin|with Hole|Stud Hole|Handle|Clip"
    r"|Ball Joint|Hinge|Turntable|Socket|Bar |Groove and"
    # Widening FAMILIES let a second kind of part through: things that are
    # shaped like nothing a wall can use. A minifigure's sword matches no
    # architectural family on its own, but "Large Figure Weapon" and its
    # neighbours sit next to the wedges and shells in the catalogue.
    r"|Large Figure|Creature|Headwear|Weapon|Sword|Gun |Clikits|Hose"
    r"|Bionicle|Accessory|Helmet|Armour|Armor|Costume)",
    re.I,
)

HEADER = '''"""Measured LEGO shapes. GENERATED — do not edit by hand.

Regenerate with scripts/build_shape_library.py. Every field below was read out of
the official LDraw geometry or counted from Rebrickable's set inventories; none of
it was recalled. `slope_dir` in particular is the number that decides how a slope
has to be rotated, and it is the one thing about a part that cannot be worked out
from its name.

{count} shapes, each appearing in at least {min_sets} released sets.
"""

from typing import NamedTuple


class Shape(NamedTuple):
    part_num: str
    name: str
    family: str
    width: int  # studs along LDraw +X
    depth: int  # studs along LDraw +Z
    height: float  # LDU, studs excluded
    # Where the part's origin sits inside its own geometry. There is no single
    # convention in the library — a Brick 1x1 runs y -4..24 (origin on the top
    # face) and a Cheese Slope runs -15.6..0 (origin on the bottom) — so to seat
    # a part on a surface at world Y = s, put its origin at s - y_max.
    y_min: float
    y_max: float
    # Horizontal extents, for the same reason. 3040b spans z -30..+10: its
    # footprint centre is at -10, not 0. Assuming a part is centred on its origin
    # puts every slope one stud out of place, and never says so.
    x_min: float
    x_max: float
    z_min: float
    z_max: float
    has_studs: bool
    # Which way the part's one large flat face points, along Z, for parts that
    # have one: "+z", "-z", or None when the two sides are alike. Measured as
    # area, not assumed — every panel in the library faces +z except Panel
    # 1 x 6 x 5, which faces -z, and a panel mounted the wrong way round shows
    # its supporting ribs to the camera without any error being raised.
    wall_side: str | None
    # Which horizontal axis the top surface descends along, and in which
    # direction, measured off the vertices. None for a flat-topped part.
    slope_axis: str | None
    slope_dir: str | None
    slope_drop: float
    sets: int  # set inventories this part appears in


SHAPES: list[Shape] = [
'''

FOOTER = ''']

BY_PART: dict[str, Shape] = {{s.part_num: s for s in SHAPES}}


def family(name: str) -> list[Shape]:
    """Every shape in one family, commonest first."""
    return [s for s in SHAPES if s.family == name]


def fitting(name: str, width: int, depth: int) -> list[Shape]:
    """Shapes in a family with exactly this footprint, commonest first."""
    return [s for s in family(name) if s.width == width and s.depth == depth]


FAMILIES: tuple[str, ...] = {families}
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ldraw", required=True, help="unpacked LDraw library (holds parts/ and p/)")
    ap.add_argument("--data", required=True, help="directory with parts.csv and inventory_parts.csv")
    ap.add_argument(
        "--min-sets",
        type=int,
        default=DEFAULT_MIN_SETS,
        help=f"drop parts appearing in fewer set inventories than this (default {DEFAULT_MIN_SETS})",
    )
    ap.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "app/services/lego_shapes.py"),
    )
    args = ap.parse_args()

    os.environ["LDRAW_DIR"] = args.ldraw
    import measure_ldraw

    measure_ldraw.LIB = args.ldraw

    inventories: dict[str, set[str]] = collections.defaultdict(set)
    with open(Path(args.data) / "inventory_parts.csv", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            inventories[row["part_num"]].add(row["inventory_id"])
    freq = {k: len(v) for k, v in inventories.items()}
    print(f"commonness for {len(freq)} parts", file=sys.stderr)

    def family_of(name: str) -> str | None:
        for fam, pattern in FAMILIES:
            if re.match(pattern, name, re.I):
                return fam
        return None

    kept: list[dict] = []
    dropped: collections.Counter[str] = collections.Counter()
    with open(Path(args.data) / "parts.csv", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            name, part = r["name"], r["part_num"]
            fam = family_of(name)
            if not fam:
                continue
            if SKIP.search(name) or SKIP.search(part):
                dropped["variant of another shape"] += 1
                continue
            if freq.get(part, 0) < args.min_sets:
                dropped["too rare to source"] += 1
                continue
            m = measure_ldraw.measure(part)
            if not m:
                dropped["no LDraw geometry"] += 1
                continue
            w, d = m["widthStuds"], m["depthStuds"]
            # Studs are whole numbers. A fractional footprint cannot be placed on
            # the grid this generator builds on.
            if abs(w - round(w)) > 0.05 or abs(d - round(d)) > 0.05:
                dropped["off-grid footprint"] += 1
                continue
            m.update(name=name, family=fam, sets=freq[part],
                     widthStuds=int(round(w)), depthStuds=int(round(d)))
            kept.append(m)

    kept.sort(key=lambda m: (m["family"], -m["sets"], m["part"]))
    families = tuple(sorted({m["family"] for m in kept}))

    lines = [HEADER.format(count=len(kept), min_sets=args.min_sets)]
    for m in kept:
        lines.append(
            "    Shape({part!r}, {name!r}, {family!r}, {w}, {d}, {h}, {ymin}, {ymax}, "
            "{xmin}, {xmax}, {zmin}, {zmax}, "
            "{studs}, {ws!r}, {sa!r}, {sd!r}, {drop}, {sets}),\n".format(
                part=m["part"], name=m["name"], family=m["family"],
                w=m["widthStuds"], d=m["depthStuds"], h=m["heightLDU"],
                ymin=m["yMinLDU"], ymax=m["yMaxLDU"],
                xmin=m["xMinLDU"], xmax=m["xMaxLDU"],
                zmin=m["zMinLDU"], zmax=m["zMaxLDU"], studs=m["hasStuds"],
                ws=m["wallSide"],
                sa=m["slopeAxis"], sd=m["slopeDir"], drop=m["slopeDrop"], sets=m["sets"],
            )
        )
    lines.append(FOOTER.format(families=families))
    Path(args.out).write_text("".join(lines))

    by_family = collections.Counter(m["family"] for m in kept)
    print(f"\nwrote {len(kept)} shapes to {args.out}", file=sys.stderr)
    for fam, n in by_family.most_common():
        print(f"  {n:4d}  {fam}", file=sys.stderr)
    print(f"\ndropped: {dict(dropped)}", file=sys.stderr)


if __name__ == "__main__":
    main()
