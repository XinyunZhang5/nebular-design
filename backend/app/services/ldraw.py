"""Export a build plan as LDraw, the open LEGO CAD format.

Writing our own renderer was the wrong instinct: LDraw is the standard the whole
LEGO CAD ecosystem already speaks, and emitting it is just text. Once a plan is
an .ldr file you get, for free:

  * BrickLink Studio 2.0 — photorealistic render, auto-generated step-by-step
    instructions, and one-click ordering of every part in the model
  * LeoCAD / LDView — free cross-platform viewers
  * three.js LDrawLoader — interactive 3D in the browser, real part geometry

Everything below was checked against the official library rather than recalled:

  Geometry   1 stud = 20 LDU across; 1 brick = 24 LDU tall; +Y points DOWN.
             Brick origins sit at the centre of the TOP face — 3005.dat's body
             spans Y 0..24 with its stud reaching up to -4, i.e. the body hangs
             below the origin. Measured, not recalled: see the bbox table in the
             fetch script's output.
  Rotation   "Brick 2 x 4" is 4 studs along X and 2 along Z (3001.dat spans
             X -40..40, Z -20..20), so the LONGER side is native to X. A brick
             placed the other way round needs a quarter turn about Y.
  Colours    LDraw colour codes are NOT Rebrickable colour IDs. Most coincide,
             but some collide outright — see LDRAW_CODE below.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from app.services import lego_catalogue as cat
from app.services import lego_shapes as shapes

logger = logging.getLogger(__name__)

STUD_LDU = 20  # one stud, horizontally
BRICK_LDU = 24  # one course, vertically

# Imported rather than redefined: the step meta below has to fall on the same
# course boundaries the written instructions use, or the playback and the booklet
# disagree about what step 3 is.
from app.services.legolize import COURSES_PER_STEP, FLOOR  # noqa: E402

IDENTITY = "1 0 0 0 1 0 0 0 1"
ROT_Y_90 = "0 0 -1 0 1 0 1 0 0"
ROT_Y_180 = "-1 0 0 0 1 0 0 0 -1"
ROT_Y_270 = "0 0 1 0 1 0 -1 0 0"

# The rotation matrices as numbers, for working out where a rotated part actually
# lands. p' = (-z, y, x) for a quarter turn, p' = (z, y, -x) for the other.
#
# "y0" and "y180" exist for the same reason the quarter turns do. A relief has
# one silhouette and its roof slopes only ever descend across the facade, so two
# turns covered it. A solid has four sides, and a slope on the back wall has to
# descend the other way down Z — which is the half turn — while one on the front
# needs no turn at all but still needs its centre measured, because a slope is
# not centred on its own origin and the untuned path assumes parts are.
_TURN = {
    "y0": (IDENTITY, lambda x, z: (x, z)),
    "y90": (ROT_Y_90, lambda x, z: (-z, x)),
    "y180": (ROT_Y_180, lambda x, z: (-x, -z)),
    "y270": (ROT_Y_270, lambda x, z: (z, -x)),
}


def _rotated_centre(shape, turn: str) -> tuple[float, float]:
    """Where a turned part's footprint centre sits relative to its origin.

    Ordinary bricks are centred on their own origin, so the placement maths could
    ignore this and did. Slopes are not: 3040b spans z from -30 to +10, putting its
    footprint centre a whole stud off. Turn that part and place it as though it
    were centred and every roof slope lands one stud away from the step it was
    meant to sit on — visibly wrong, and silently so.
    """
    _, turn_fn = _TURN[turn]
    xs, zs = zip(
        *(turn_fn(x, z)
          for x in (shape.x_min, shape.x_max)
          for z in (shape.z_min, shape.z_max))
    )
    return (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2

# Rebrickable colour ID -> LDraw colour code.
#
# Generated, not kept by hand: see scripts/build_colour_table.py, which matches
# every colour against the official LDConfig.ldr by name first and RGB second.
# The hand-kept version listed six exceptions and was correct for the 43-colour
# palette it was written against. Widening that palette to 137 left 34 colours —
# Warm Tan and Sienna Brown among them, which are most of Big Ben — with no
# LDraw code at all, and an unresolvable code does not fail: the viewer just
# draws the part in the wrong colour. The generated map reproduces all six of
# the hand-checked exceptions and covers the rest.
from app.services.lego_colours import LDRAW_CODE

# LDraw renamed this one; the old number still resolves as an alias, but the
# canonical file is what viewers expect to find.
LDRAW_PART: dict[str, str] = {"3023": "3023b"}


def _colour(rebrickable_id: int) -> int:
    return LDRAW_CODE.get(rebrickable_id, rebrickable_id)


def _part(part_num: str) -> str:
    return LDRAW_PART.get(part_num, part_num)




def to_ldraw(
    cells: Iterable[Any],
    width: int,
    courses: int,
    depth: int,
    name: str = "Nebular build",
) -> str:
    """Render a standing model as an LDraw file.

    Axis mapping, and why each one is what it is:

      x   studs across the facade      ->  LDraw +X, unchanged
      y   courses upward               ->  LDraw -Y, because LDraw's +Y is down
      z   studs into the model         ->  LDraw +Z *reversed*

    The reversal matters. Model z counts from the back plane forward, because that
    is the order the fill is generated in; LDraw viewers put the camera on +Z and
    look toward the origin, so leaving it alone would show the flat back of the
    wall and hide the picture. Flipping it here costs one subtraction and means
    every viewer opens on the facade.
    """
    lines = [
        f"0 {name}",
        "0 Name: nebular.ldr",
        "0 Author: Nebular Design",
        "0 !LDRAW_ORG Model",
        f"0 // {width} studs wide, {courses} courses tall, {depth} studs deep",
        "",
    ]

    # Emit course by course with a STEP meta between bands. Viewers that understand
    # STEP (LDrawLoader, Studio, LPub3D) then give step-by-step playback for free,
    # in the same bottom-up order as the written instructions.
    ordered = sorted(cells, key=lambda c: (c.y, c.z, c.x))
    count = 0
    current_band = None
    for c in ordered:
        band = -1 if c.y == FLOOR else c.y // COURSES_PER_STEP
        if current_band is not None and band != current_band:
            lines.append("0 STEP")
        current_band = band

        bw, bd = c.brick.width, c.brick.length
        turn = getattr(c, "rot", None)
        if turn:
            # An explicit turn: the cell already knows which way the part has to
            # face, so the centring has to come off the measured geometry rather
            # than from assuming the part fills its footprint symmetrically.
            matrix, _ = _TURN[turn]
            cx, cz = _rotated_centre(shapes.BY_PART[c.brick.part_num], turn)
            x = (c.x + bw / 2) * STUD_LDU - cx
            z = (depth - c.z - bd / 2) * STUD_LDU - cz
        else:
            # Native orientation puts the longer side on X; turn the brick a
            # quarter turn when the model wants the longer side running into the
            # facade.
            matrix = IDENTITY if bw >= bd else ROT_Y_90
            x = (c.x + bw / 2) * STUD_LDU
            z = (depth - c.z - bd / 2) * STUD_LDU
        # Every part's origin is the centre of its top face. The floor's top is the
        # ground course's underside, so it sits at 0; course n's top is n+1 courses
        # above that, and -Y is up. A part spanning several courses has its top
        # that many courses up, not one.
        y = 0.0 if c.y == FLOOR else -BRICK_LDU * (c.y + getattr(c, "courses", 1))
        # A cap rests on that course rather than replacing it, so its own top face
        # is one part-height further up. Reading the height off the part instead of
        # assuming a tile keeps this correct if a cap is ever something else.
        if getattr(c, "cap", False):
            y -= c.brick.height
        lines.append(
            f"1 {_colour(c.colour_id)} {x:.1f} {y:.1f} {z:.1f} {matrix} "
            f"{_part(c.brick.part_num)}.dat"
        )
        count += 1

    lines.append("")
    logger.info("Wrote %d LDraw part lines", count)
    return "\n".join(lines)
