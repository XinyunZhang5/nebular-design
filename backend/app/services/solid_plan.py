"""Turn a lattice solid into a build plan: real parts, real colours, real steps.

`legolize.generate_plan` does this for the relief, and everything it does below
the geometry — greedy rectangle partitioning, the colour clustering, the parts
tally, the step bands — applies unchanged to a solid. What cannot carry over is
the shape of the input: the relief is a `depths[course, stud]` heightfield, one
number per column, and a reconstructed building is not a heightfield. So the
geometry-facing half is rewritten here and the rest is imported.

WHY THE SOLID IS HOLLOWED

A filled 48-stud tower is forty thousand cells. Partitioned into the largest
bricks that fit it is still several thousand pieces of buried fill, which is
both unbuyable and pointless: nobody sees them and they exist only to hold up
the course above. Keeping a shell a couple of cells thick is what a real set
does. The catch is that hollowing can leave a course resting on air — the ring
of an upper storey can sit inboard of the ring below it — so every cell removed
is put back if something above it needed it.

TWO PASSES ON SUPPORT, AND WHY BOTH

`_repair_support` restores interior brick that the hollowing took out from under
something. It works on connected groups within a course, which is optimistic:
it assumes the course above will be bricked so that the run reaches its anchor.
`_partition_anchored` is the pass that makes that true or admits it did not —
every brick it lays has to cover at least one cell that is held from below, and
whatever it cannot lay is dropped from the model rather than counted. The first
pass keeps the model whole; the second keeps it honest.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import numpy as np

from app.services import lego_catalogue as cat
from app.services.legolize import (
    BRICK_LDU,
    DEFAULT_MAX_COLOURS,
    FLOOR,
    STUD_LDU,
    Cell,
    _assembly_steps,
    _choose_palette,
    _partition,
    _redmean,
    _tally,
)
from app.services import lego_shapes as shapes
from app.services.voxel import COURSE_PER_STUD, Solid

logger = logging.getLogger(__name__)

# How many cells of brick to keep behind every surface. One is a paper-thin
# shell that reads as a shell wherever a course steps back; two holds an edge.
# The page these renders land on, so a render never carries a border of a
# colour the site does not use.
BACKGROUND = (243, 242, 238)

DEFAULT_SHELL_CELLS = 2

# Give up on the support fixed point after this many sweeps. Two or three is
# typical; the cap only stops a pathological mesh from hanging the request.
MAX_SUPPORT_SWEEPS = 12

def _hollow(filled: np.ndarray, shell: int) -> np.ndarray:
    """Keep only the cells within `shell` of the outside."""
    from scipy import ndimage

    # Distance to the nearest empty cell, with the world outside the array
    # counted as empty — otherwise the bottom course, which touches the floor of
    # the array, reads as deep interior and gets hollowed out from under itself.
    padded = np.pad(filled, 1, constant_values=False)
    depth = ndimage.distance_transform_cdt(padded, metric="taxicab")[1:-1, 1:-1, 1:-1]
    return filled & (depth <= shell)


def _repair_support(filled: np.ndarray, original: np.ndarray) -> np.ndarray:
    """Put back interior wherever hollowing left a whole run standing on air.

    Deliberately at the level of a connected group within a course, not a single
    cell. Cell by cell was the second attempt and it refills the entire model:
    the inner cell of a tapered ring sits over the hollow, so it demands a cell
    beneath, which demands another, all the way to the ground — every taper
    grows a solid column and hollowing buys nothing.

    The looser rule is the physically true one, because a course is laid in
    bricks and a brick spanning several cells only needs one of them held. That
    is `_partition_anchored`'s job. This pass exists for what that cannot save:
    a run with no anchor anywhere along it, which no brick can reach.

    Runs to a fixed point — a restored cell needs support of its own.
    """
    from scipy import ndimage

    out = filled.copy()
    for sweep in range(MAX_SUPPORT_SWEEPS):
        added = 0
        for y in range(1, out.shape[0]):
            if not out[y].any():
                continue
            labels, n = ndimage.label(out[y])
            if not n:
                continue
            held = ndimage.sum_labels(out[y - 1], labels, index=np.arange(1, n + 1)) > 0
            if held.all():
                continue
            need = np.isin(labels, np.flatnonzero(~held) + 1)
            # Only ever put back cells the reconstruction said were solid; a
            # column invented outside the building would be a brick hanging in
            # space, which is worse than the hole it fills.
            put = need & original[y - 1] & ~out[y - 1]
            if not put.any():
                continue
            out[y - 1] |= put
            added += int(put.sum())
        if not added:
            logger.info("solid_plan: support converged after %d sweep(s)", sweep + 1)
            return out
    logger.warning("solid_plan: support did not converge in %d sweeps", MAX_SUPPORT_SWEEPS)
    return out


def _visible(filled: np.ndarray) -> np.ndarray:
    """Cells with at least one face open to the air."""
    padded = np.pad(filled, 1, constant_values=False)
    exposed = np.zeros_like(filled)
    for axis in range(3):
        for shift in (-1, 1):
            sl = [slice(1, -1)] * 3
            sl[axis] = slice(1 + shift, (-1 + shift) or None)
            exposed |= ~padded[tuple(sl)]
    return exposed & filled


def _face_forward(rgb: np.ndarray, filled: np.ndarray, visible: np.ndarray) -> np.ndarray:
    """Repaint the surfaces the camera could not see with the colour in front of them.

    The reconstruction hands back a colour for the whole surface, but only the
    front of it was ever observed. Everywhere else the model is guessing, and it
    guesses dark — an unlit side comes back near-black, and the colour
    clustering then spends most of its palette on shadow. Big Ben came out black
    and dark green on three sides out of four.

    A photograph cannot say what colour the back is. What it can say is what
    colour the building is at that height and that position across the facade,
    which for a building — overwhelmingly symmetric, banded by storey — is the
    better guess by a wide margin.

    Which faces to leave alone matters as much as which to repaint. The first
    version repainted every cell in a column, and a flat roof is a column's
    worth of cells at one height: each took the colour of the roof's front edge
    and the whole surface came out in horizontal stripes, worst on exactly the
    wide low buildings the reconstruction already struggles with. A face that
    points at the camera or at the sky was seen; only the sides, the back and
    the undersides are guesses, and only those are repainted.
    """
    n_depth = filled.shape[1]
    padded = np.pad(filled, 1, constant_values=False)
    seen_front = ~padded[1:-1, 2:, 1:-1]  # +depth face open: faces the camera
    seen_top = ~padded[2:, 1:-1, 1:-1]  # +course face open: faces the sky
    guessed = visible & ~(seen_front | seen_top)
    if not guessed.any():
        return rgb

    order = np.arange(n_depth)[None, :, None]
    frontmost = np.where(filled, order, -1).max(axis=1)  # (courses, studs)
    out = rgb.copy()
    yy, zz, xx = np.nonzero(guessed)
    front_z = frontmost[yy, xx]
    ok = front_z >= 0
    out[yy[ok], zz[ok], xx[ok]] = rgb[yy[ok], front_z[ok], xx[ok]]
    return out


def _quantise(rgb: np.ndarray, visible: np.ndarray, max_colours: int) -> np.ndarray:
    """Colour ID for every visible cell; the fill colour everywhere else."""
    ids_out = np.full(visible.shape, cat.FILL_COLOUR_ID, dtype=np.int32)
    samples = rgb[visible].astype(np.float32)
    if not len(samples):
        return ids_out
    palette_ids = np.array(_choose_palette(samples, max_colours), dtype=np.int32)
    palette = np.array(
        [cat.COLOURS_BY_ID[int(i)].rgb for i in palette_ids], dtype=np.float32
    )
    ids_out[visible] = palette_ids[_redmean(samples, palette).argmin(axis=1)]
    return ids_out


# Runs longest first, so a gentle step gets the shallow part and a sharp one
# falls back to the 45 degree family.
SLOPE_RUNS: tuple[int, ...] = (6, 4, 3, 2)

# Which quarter turn makes a slope descend a given way in model axes, keyed by
# the step direction as (depth, stud). Every part in the table below is cut to
# descend along its own -Z; model +z maps to LDraw -Z, so the untuned part falls
# toward the front of the model and the other three follow from that.
SLOPE_TURNS: dict[tuple[int, int], str] = {
    (1, 0): "y0",     # descending toward the front
    (-1, 0): "y180",  # toward the back
    (0, 1): "y90",    # toward +x across the facade
    (0, -1): "y270",  # toward -x
}


def _slope_table() -> dict[tuple[int, int], Any]:
    """(run, width) -> the commonest full-course slope with that footprint.

    Restricted to parts a course tall that descend along their own -Z, so a
    single turn table covers all four directions. The library holds slopes at
    other heights — the 2/3-height "cheese" family among them — but a part that
    is not a full course cannot replace the course it sits in, and stacking one
    on top changes the model's height.
    """
    table: dict[tuple[int, int], Any] = {}
    for shape in shapes.SHAPES:
        if shape.family != "slope" or abs(shape.height - BRICK_LDU) > 0.01:
            continue
        if shape.slope_axis != "z" or shape.slope_dir != "-":
            continue
        key = (shape.depth, shape.width)  # run along z, width across x
        if key not in table or shape.sets > table[key].sets:
            table[key] = shape
    return table


SLOPES = _slope_table()
SLOPE_WIDTHS: dict[int, list[int]] = {
    run: sorted({w for r, w in SLOPES if r == run}, reverse=True)
    for run in {r for r, _ in SLOPES}
}


def _shift(a: np.ndarray, dz: int, dx: int) -> np.ndarray:
    """`a` moved by (dz, dx), with False shifted in at the edges."""
    out = np.zeros_like(a)
    zs = slice(max(dz, 0), a.shape[0] + min(dz, 0))
    xs = slice(max(dx, 0), a.shape[1] + min(dx, 0))
    zt = slice(max(-dz, 0), a.shape[0] + min(-dz, 0))
    xt = slice(max(-dx, 0), a.shape[1] + min(-dx, 0))
    out[zs, xs] = a[zt, xt]
    return out


def _roofline(
    filled: np.ndarray, colours: np.ndarray
) -> tuple[list[Cell], np.ndarray]:
    """Replace the staircase in the silhouette with slope bricks.

    A voxel model's outline is a staircase on every side, which is what makes it
    read as a voxel model. Where the steps are regular a slope is the part a
    builder would actually reach for, and it takes the place of the top course
    brick rather than sitting on it — it *is* that course, so nothing about the
    model's height or coverage changes.

    The relief version of this ran along one axis because a wall has one
    silhouette. A solid has four, so this sweeps all four directions; longer
    runs first, so a gentle step gets the 18 or 33 degree part before the 45.

    Returns the slopes and a mask of the cells they occupy, so the ordinary
    partition can leave those cells alone.
    """
    courses, depth, width = filled.shape
    reserved = np.zeros_like(filled)
    out: list[Cell] = []

    for y in range(courses - 1):
        layer = filled[y]
        if not layer.any():
            continue
        # Cells with open sky. Only these can hold a slope: a cell with brick on
        # top has to be a full brick or the model gains a hole.
        top = layer & ~filled[y + 1]
        if not top.any():
            continue
        held = np.ones_like(layer) if y == 0 else filled[y - 1]

        for (dz, dx), turn in SLOPE_TURNS.items():
            for run in SLOPE_RUNS:
                if run not in SLOPE_WIDTHS:
                    continue
                # A ledge of `run` cells, all of them top cells, all resting on
                # something, with the wall carrying on upward behind the first
                # and open air past the last.
                ledge = top & ~reserved[y] & held
                for i in range(1, run):
                    ledge &= _shift(top & ~reserved[y] & held, -i * dz, -i * dx)
                ledge &= _shift(filled[y + 1], dz, dx)
                ledge &= ~_shift(layer, -run * dz, -run * dx)
                if not ledge.any():
                    continue

                # Group the starts that sit side by side across the run, so one
                # wide slope replaces a row of narrow ones.
                across = (abs(dx), abs(dz))  # perpendicular to the run
                for z0, x0 in map(tuple, np.argwhere(ledge)):
                    if reserved[y, z0, x0]:
                        continue
                    span = 0
                    while (
                        ledge[z0 + span * across[0], x0 + span * across[1]]
                        if 0 <= z0 + span * across[0] < depth
                        and 0 <= x0 + span * across[1] < width
                        else False
                    ):
                        if reserved[y, z0 + span * across[0], x0 + span * across[1]]:
                            break
                        span += 1
                    if not span:
                        continue
                    w = next((c for c in SLOPE_WIDTHS[run] if c <= span), None)
                    if w is None:
                        continue
                    shape = SLOPES[(run, w)]

                    cells_z = [z0 + i * dz + j * across[0] for i in range(run) for j in range(w)]
                    cells_x = [x0 + i * dx + j * across[1] for i in range(run) for j in range(w)]
                    reserved[y, cells_z, cells_x] = True

                    # Footprint in model axes: the run lies along whichever axis
                    # the step travels, the width across the other.
                    bw = w if dx == 0 else run
                    bl = run if dx == 0 else w
                    cx, cz = min(cells_x), min(cells_z)
                    out.append(
                        Cell(
                            cx, y, cz,
                            cat.Plate(shape.part_num, shape.name, bw, bl),
                            int(colours[y, z0, x0]),
                            hidden=False,
                            rot=turn,
                        )
                    )
    return out, reserved


def _partition_anchored(
    mask: np.ndarray, anchored: np.ndarray, catalogue
) -> tuple[list[tuple[int, int, Any]], np.ndarray]:
    """Greedy rectangle cover where every brick has to land on something.

    `legolize._partition` covers a mask with the biggest bricks that fit. That is
    the right algorithm and the wrong constraint for a solid: a reconstruction
    has overhangs, and a brick laid entirely over open air is not a brick, it is
    a claim. A real one only needs *one* stud of its footprint held — that is how
    an arch is bricked, each course reaching a stud further over the opening — so
    the rule here is that the window must touch `anchored` somewhere.

    Returns the placements and the cells it could not place, which are the ones
    genuinely floating in mid-air.
    """
    rows, cols = mask.shape
    covered = np.zeros_like(mask, dtype=bool)
    out: list[tuple[int, int, Any]] = []

    for r in range(rows):
        for c in range(cols):
            if not mask[r, c] or covered[r, c]:
                continue
            placed = False
            for brick in catalogue:
                for bw, bl in {(brick.width, brick.length), (brick.length, brick.width)}:
                    # Four placements per size, with this cell at each corner of
                    # the brick. Growing only down-and-right — which is what the
                    # scan order makes natural, and what the first version did —
                    # means a cell whose only anchor lies up or to the left can
                    # never be covered by a brick that reaches it, and gets
                    # dropped although it is perfectly buildable.
                    for r0, c0 in {(r, c), (r, c - bw + 1), (r - bl + 1, c), (r - bl + 1, c - bw + 1)}:
                        if r0 < 0 or c0 < 0 or r0 + bl > rows or c0 + bw > cols:
                            continue
                        window = (slice(r0, r0 + bl), slice(c0, c0 + bw))
                        if (
                            mask[window].all()
                            and not covered[window].any()
                            and anchored[window].any()
                        ):
                            covered[window] = True
                            out.append((c0, r0, brick._replace(width=bw, length=bl)))
                            placed = True
                            break
                    if placed:
                        break
                if placed:
                    break
    return out, mask & ~covered


def _course_cells(
    layer: np.ndarray,
    seen: np.ndarray,
    colours: np.ndarray,
    anchored: np.ndarray,
    y: int,
) -> tuple[list[Cell], np.ndarray]:
    """Every brick in one course, plus the cells that turned out to be floating.

    Two partitions, for the same reason the relief has two: the cells you can see
    have to be grouped by colour so no brick straddles two of them, and the
    buried ones are all one colour and can take the widest parts in the
    catalogue. The partition runs in the (depth, stud) plane, so a 2x4 can lie
    along either axis and span two studs of depth.
    """
    cells: list[Cell] = []
    dropped = np.zeros_like(layer)

    for colour_id in np.unique(colours[seen]):
        mask = seen & (colours == colour_id)
        if not mask.any():
            continue
        placed, leftover = _partition_anchored(mask, anchored, cat.BRICKS_BY_AREA)
        cells.extend(
            Cell(x, y, z, brick, int(colour_id), hidden=False) for x, z, brick in placed
        )
        dropped |= leftover

    buried = layer & ~seen
    if buried.any():
        placed, leftover = _partition_anchored(buried, anchored, cat.BRICKS_BY_AREA)
        cells.extend(
            Cell(x, y, z, brick, cat.FILL_COLOUR_ID, hidden=True) for x, z, brick in placed
        )
        dropped |= leftover

    return cells, dropped


def _floor(footprint: np.ndarray) -> list[Cell]:
    """Plates under the ground course, covering exactly what stands on them."""
    return [
        Cell(x, FLOOR, z, plate, cat.FILL_COLOUR_ID, hidden=True)
        for x, z, plate in _partition(footprint, cat.PLATES_BY_AREA)
    ]


def _unsupported(cells: list[Cell], filled: np.ndarray) -> int:
    """Bricks with no brick beneath any of their studs. Should be zero."""
    loose = 0
    for c in cells:
        if c.y <= 0:
            continue
        below = filled[c.y - 1, c.z : c.z + c.brick.length, c.x : c.x + c.brick.width]
        if not below.any():
            loose += 1
    return loose


def _build_courses(
    filled: np.ndarray,
    visible: np.ndarray,
    colours: np.ndarray,
    reserved: np.ndarray | None,
) -> tuple[list[Cell], int]:
    """Brick every course bottom-up, dropping whatever will not stand.

    Bottom-up so that "supported" means supported by what is actually there
    after the course below dropped its own floating cells — not by what the mesh
    wanted to be there. Mutates `filled` and `visible` to match what it built.
    """
    cells: list[Cell] = []
    dropped_total = 0
    for y in range(len(filled)):
        if not filled[y].any():
            continue
        anchored = np.ones_like(filled[y]) if y == 0 else filled[y - 1]
        skip = None if reserved is None else reserved[y]
        layer = filled[y] if skip is None else filled[y] & ~skip
        seen = visible[y] if skip is None else visible[y] & ~skip
        course, dropped = _course_cells(layer, seen, colours[y], anchored, y)
        if dropped.any():
            filled[y] &= ~dropped
            visible[y] &= ~dropped
            dropped_total += int(dropped.sum())
        cells.extend(course)
    return cells, dropped_total


def plan_from_solid(
    solid: Solid,
    shell: int | None = DEFAULT_SHELL_CELLS,
    max_colours: int = DEFAULT_MAX_COLOURS,
) -> dict[str, Any]:
    """Lattice solid -> the same plan shape `legolize.generate_plan` returns."""
    filled = solid.filled.copy()
    if shell:
        filled = _repair_support(_hollow(filled, shell), filled)
        logger.info(
            "solid_plan: hollowed %d cells to %d (shell %d)",
            solid.count, int(filled.sum()), shell,
        )

    courses, depth, width = filled.shape
    visible = _visible(filled)
    colours = _quantise(_face_forward(solid.rgb, filled, visible), visible, max_colours)

    # Bottom-up, so "supported" means supported by what is actually there after
    # the course below dropped its own floating cells — not by what the mesh
    # wanted to be there.
    # Two passes, because the two steps each need the other's answer.
    #
    # A slope may only sit on a cell that is actually held, and which cells those
    # are is not known until the ordinary partition has run and thrown away the
    # ones it could not anchor. Placing slopes first put 22 of them on support
    # that the very next pass deleted. So: build once to let the solid settle,
    # then find the staircase in what survived, then build again for real. The
    # partition is a tenth of a second; the reconstruction above it is eight.
    _, dropped_total = _build_courses(filled, visible, colours, None)

    # A slope replaces the top brick of its course rather than sitting on it, so
    # the solid is unchanged and everything anchored against it still is.
    slopes, reserved = _roofline(filled, colours)
    logger.info(
        "solid_plan: %d slope(s) over %d cell(s) of staircase",
        len(slopes), int(reserved.sum()),
    )
    cells, again = _build_courses(filled, visible, colours, reserved)
    cells.extend(slopes)
    dropped_total += again

    floor = _floor(filled[0])
    bricks = _tally(cells + floor)
    total_pieces = sum(b["quantity"] for b in bricks)

    by_colour: Counter[int] = Counter()
    for b in bricks:
        if not b["hidden"]:
            by_colour[b["colorId"]] += b["quantity"]
    palette = [
        {
            "name": cat.COLOURS_BY_ID[cid].name,
            "hex": cat.COLOURS_BY_ID[cid].hex,
            "colorId": cid,
            "quantity": qty,
        }
        for cid, qty in by_colour.most_common()
    ]

    minutes = total_pieces * 0.16
    difficulty = (
        "Beginner" if total_pieces < 400
        else "Intermediate" if total_pieces < 1400
        else "Expert"
    )

    return {
        "difficulty": difficulty,
        "estimatedPieceCount": total_pieces,
        "estimatedTime": f"{max(1, round(minutes / 60))}–{max(2, round(minutes / 60) + 1)} hours",
        "colorPalette": palette,
        "bricks": bricks,
        "steps": _assembly_steps(cells, courses, floor),
        "base": {
            "name": "Plate floor",
            "quantity": len(floor),
            "widthStuds": width,
            "depthStuds": depth,
        },
        "grid": {
            "width": width,
            "courses": courses,
            "depth": depth,
            "sizeCm": {
                "width": round(width * STUD_LDU * 0.04, 1),
                "height": round(courses * BRICK_LDU * 0.04, 1),
                "depth": round(depth * STUD_LDU * 0.04, 1),
            },
            "cells": width * courses * depth,
            "buildingCells": int(filled.sum()),
            "coverage": round(float(filled.mean()), 3),
        },
        "structure": {
            "unsupportedPieces": _unsupported(cells, filled),
            "droppedCells": dropped_total,
        },
        "visiblePieceCount": sum(b["quantity"] for b in bricks if not b["hidden"]),
        "hiddenPieceCount": sum(b["quantity"] for b in bricks if b["hidden"]),
        # numpy arrays and Cell tuples — for the renderers and the LDraw writer.
        # Drop these before the plan goes near JSON or the database.
        "_cells": cells + floor,
        "_solid": filled,
        "_colours": colours,
    }


# ---------------------------------------------------------------- renders


def _shade(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(int(max(0, min(255, c * factor))) for c in rgb)  # type: ignore[return-value]


def render_isometric(
    filled: np.ndarray, colours: np.ndarray, cell: int = 12, azimuth: int = 0
) -> "Image.Image":
    """Draw the solid as stacked isometric cubes, seen from one of four corners.

    A relief only ever had one worth looking at. A solid has four, and being
    able to turn it is the whole difference between this and the old pipeline,
    so the renderer takes which corner to stand at rather than assuming.

    Painter's algorithm: back to front, top-down within a column. There is no
    depth buffer and none is needed — cubes on a lattice never interpenetrate,
    so drawing them in order is exact.
    """
    from PIL import Image, ImageDraw

    courses, depth, width = filled.shape
    turn = azimuth % 4

    def rotate(x: int, z: int) -> tuple[int, int]:
        return [
            (x, z),
            (depth - 1 - z, x),
            (width - 1 - x, depth - 1 - z),
            (z, width - 1 - x),
        ][turn]

    tall = int(cell * COURSE_PER_STUD)
    img = Image.new(
        "RGB",
        ((width + depth) * cell + cell * 4,
         (width + depth) * cell // 2 + courses * tall + cell * 4),
        BACKGROUND,
    )
    draw = ImageDraw.Draw(img)
    ox, oy = cell * 2 + depth * cell, cell * 2

    cubes = np.argwhere(filled).tolist()
    # Farthest first: down-screen is +x+z, so sort by the difference and then by
    # height, and every cube lands on top of whatever it should hide.
    cubes.sort(key=lambda c: (rotate(c[2], c[1])[1] - rotate(c[2], c[1])[0], -c[0]))
    for y, z, x in cubes:
        rx, rz = rotate(x, z)
        sx = ox + (rx - rz) * cell
        sy = oy + (rx + rz) * cell // 2 + (courses - 1 - y) * tall
        rgb = cat.COLOURS_BY_ID[int(colours[y, z, x])].rgb
        draw.polygon(
            [(sx, sy), (sx + cell, sy + cell // 2), (sx, sy + cell), (sx - cell, sy + cell // 2)],
            fill=_shade(rgb, 1.12),
        )
        draw.polygon(
            [(sx - cell, sy + cell // 2), (sx, sy + cell),
             (sx, sy + cell + tall), (sx - cell, sy + cell // 2 + tall)],
            fill=_shade(rgb, 0.72),
        )
        draw.polygon(
            [(sx + cell, sy + cell // 2), (sx, sy + cell),
             (sx, sy + cell + tall), (sx + cell, sy + cell // 2 + tall)],
            fill=_shade(rgb, 0.92),
        )
    return img
