"""Turn a photo plus its depth map into a buildable, free-standing LEGO model.

This replaces the part of the pipeline that used to be guesswork. Previously a
language model was asked to invent a parts list, and nothing checked that the
parts existed or that the quantities added up — the README admitted the numbers
were "plausible rather than verified". Here the list is computed: every cell of
the model gets a colour from the photo and a depth from the depth map, the solid
is partitioned into maximal boxes, and each box resolves to a real part number.
The piece count is the number of pieces, because it was arrived at by counting.

WHAT IS BUILT

A wall that stands up, built in courses of bricks on a plate floor — not a
mosaic lying flat. The three axes are:

    x  studs across the facade   20 LDU each
    y  courses upward            24 LDU each   (a brick, not a plate)
    z  studs into the model      20 LDU each

Looking down -z you see the photograph. Looking from the side you see the
building's massing, because the facade is pushed forward where the subject was
nearer the camera. The back is a flat plane: a single photo says nothing about
what is behind the subject, so nothing is invented there.

WHY BRICKS AND NOT PLATES

The previous version stacked plates on a baseplate — a floor tile you had to
view from above. Standing that up is not a thing you can do with real parts: a
tile has no structure across its thickness. A wall is courses of bricks, each
gripping the one below, which is why the unit of height here is a brick.

WHY THE IMAGE IS RESAMPLED TO NON-SQUARE CELLS

A brick is 20 LDU wide and 24 LDU tall. Sampling the photo on a square grid and
building it in courses would stretch it vertically by 20%. The row count is
therefore chosen so the *built* wall carries the photo's proportions, not the
sampling grid's.

WHY THE SOLID IS FILLED RATHER THAN SHELLED

Every brick in a course rests on the course below. Filling from the back plane
forward to the facade makes that true by construction, for every cell that has a
neighbour beneath it. A hollow shell would need each course's footprint to line
up with the next one's, which a photograph's depth map does not promise.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, NamedTuple

import numpy as np
from PIL import Image, ImageFilter

from app.services import lego_catalogue as cat
from app.services import lego_shapes as shapes
from app.services import score as scoring
from app.services.segment import STUD_COVERAGE_THRESHOLD, clean_stud_mask

logger = logging.getLogger(__name__)

STUD_LDU = 20  # one stud, across the facade and into it
BRICK_LDU = 24  # one course, upward

# 48 studs is where a landmark's towers collapse into a few blobs and 64 gives a
# readable silhouette but no facade detail; 96 is where windows and arches survive
# the downsample, at roughly the piece count of a retail LEGO Art set.
DEFAULT_MAX_STUDS = 96

# How far the facade can travel between its nearest and farthest point. This is
# the model's depth, and the only reason it is not larger: every stud of depth is
# another course-sized layer of hidden brick behind the skin, so the piece count
# grows with it. Five studs is 100 LDU — enough that the towers of a landmark
# stand proud of the wall between them, and that the model reads as an object
# rather than a picture.
DEFAULT_RELIEF_STUDS = 5

# How many LEGO colours one model may use.
#
# Twelve while the catalogue held 43 colours, which was the real ceiling: a
# sandstone tower had no good match in it and came out grey-green whatever the
# palette budget. With 102 to draw on the budget matters less than it looks —
# measured on the same photograph, raising this to 96 took the colours actually
# used from 12 to 24 and the renders were indistinguishable past 24, because the
# clustering runs out of distinguishable colours in the image long before it
# runs out of slots. So: 24, which is where it saturates, and no higher, since
# every extra colour is another line on the shopping list.
DEFAULT_MAX_COLOURS = 24

# Pieces the score treats as the size someone will actually build.
#
# Not a hard cap — the term is a gentle square-root falloff, so a model twenty
# percent over loses about nine percent and one at triple the budget loses forty.
# Chosen against LEGO's own retail sets: the Architecture line runs 500-1,200
# pieces and the largest Art mosaics about 3,000. Before this existed the search
# had no reason at all to prefer a smaller model, and reliably picked the largest
# grid offered — 128 studs came out 102 cm wide and 2,225 pieces.
DEFAULT_PIECE_BUDGET = 1500

_KMEANS_ITERATIONS = 12


# A standing component smaller than this share of the largest one is not part of
# the subject. Generous, because a building really can have a detached wing or a
# gatehouse; a lamp post is two orders of magnitude below it.
SUBJECT_MIN_SHARE = 0.08


# The course index used for the floor. The floor is plates, not bricks, so it does
# not sit on the course grid — it sits under it.
FLOOR = -1


class Cell(NamedTuple):
    """One part in the model, in model coordinates."""

    x: int  # first stud across the facade
    y: int  # course, 0 = the ground course; FLOOR = the plate floor beneath it
    z: int  # first stud into the model, 0 = back plane
    brick: cat.Plate  # `width` runs along x, `length` along z
    colour_id: int
    hidden: bool
    # A cap sits *on top of* course y instead of occupying it — the tiles that
    # finish an exposed top edge. It adds no volume to the solid, so the coverage
    # checks and the support analysis both have to skip it, or a tile would read
    # as a brick placed outside the building.
    cap: bool = False
    # A quarter turn about the vertical, for parts whose geometry is not
    # symmetric: "y90" or "y270". Only slopes need it so far — they are cut to
    # descend along their own Z, and a roofline descends along the facade's X.
    rot: str | None = None
    # How many courses the part occupies, upward from y. One for everything that
    # is laid course by course; a panel is the exception — Panel 1 x 6 x 5 is a
    # single part standing five courses tall, and a writer that assumes one
    # course seats it four courses into the floor.
    courses: int = 1


def _floor(width: int, depth: int, columns: np.ndarray | None = None) -> list[Cell]:
    """The plate floor the wall is built on.

    Not a baseplate. Baseplates come in 16x16, 32x32 and 48x48 and nothing else,
    so putting one under a facade five studs deep leaves twenty-seven studs of
    grey hanging off the back — which is exactly what the earlier version did, and
    it dominated the model's bounding box. Ordinary plates tile the footprint
    exactly, hold the bottom course together, and are parts you already have.
    """
    # Only under the columns that actually carry a ground course. A full-width
    # rectangle was the earlier behaviour and it put metres of bare grey plate out
    # to either side of a building that occupies a third of the frame — which then
    # dominates the model's bounding box and, through that, the camera framing.
    carried = np.ones(width, dtype=bool) if columns is None else columns
    footprint = np.tile(carried, (depth, 1))
    if not footprint.any():
        footprint = np.ones((depth, width), dtype=bool)
    return [
        Cell(x, FLOOR, z, plate, cat.FILL_COLOUR_ID, hidden=True)
        for x, z, plate in _partition(footprint, cat.PLATES_BY_AREA)
    ]


# ---------------------------------------------------------------- sampling


def _sample(
    image: Image.Image,
    depth: np.ndarray,
    mask: np.ndarray | None,
    width_studs: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    """Reduce photo, depth map and mask to the brick grid, ground-up.

    Returns (rgb, depth01, mask, width, courses) with row 0 at the *bottom* of the
    picture, because row 0 is the course that sits on the floor.
    """
    src_w, src_h = image.size
    # Cells are 20 LDU wide and 24 LDU tall, so fewer rows than a square grid
    # would use. Skipping this is what would make every build look stretched.
    courses = max(1, round(width_studs * (src_h / src_w) * (STUD_LDU / BRICK_LDU)))
    size = (width_studs, courses)

    # BOX averages every source pixel in a cell. NEAREST would let a single stray
    # pixel decide a whole brick's colour.
    rgb = np.asarray(image.convert("RGB").resize(size, Image.Resampling.BOX), dtype=np.uint8)

    depth_small = np.asarray(
        Image.fromarray(depth.astype(np.float32), mode="F").resize(
            size, Image.Resampling.BOX
        ),
        dtype=np.float32,
    )

    if mask is None:
        cells = np.ones((courses, width_studs), dtype=bool)
    else:
        # Average the mask and then threshold: a cell counts as building when most
        # of its footprint is building. Sampling one pixel would make the
        # silhouette's edge depend on which pixel happened to land under it.
        coverage = np.asarray(
            Image.fromarray(mask.astype(np.float32), mode="F").resize(
                size, Image.Resampling.BOX
            ),
            dtype=np.float32,
        )
        cells = coverage >= STUD_COVERAGE_THRESHOLD
        if cells.any():
            cells = clean_stud_mask(cells)
            cells, closed = _fill_occlusions(cells)
            if closed:
                logger.info("Closed %d cells of occlusion in the silhouette", closed)
        if not cells.any():  # nothing survived — better a full wall than none
            logger.warning("Building mask emptied the grid; using the whole frame.")
            cells = np.ones((courses, width_studs), dtype=bool)

    # Normalise depth over the building only. Including the background would let a
    # distant skyline or a patch of sky set the far end of the range and squash the
    # building itself into one or two layers.
    inside = depth_small[cells]
    lo, hi = float(inside.min()), float(inside.max())
    depth01 = (
        np.zeros_like(depth_small)
        if hi - lo < 1e-6
        else np.clip((depth_small - lo) / (hi - lo), 0.0, 1.0)
    )

    # Flip so index 0 is the ground course rather than the top of the photo.
    return rgb[::-1], depth01[::-1], cells[::-1], width_studs, courses


def _redmean(samples: np.ndarray, palette: np.ndarray) -> np.ndarray:
    """Perceptual distance from every sample to every palette entry: (n,3),(k,3)->(n,k).

    The scalar form of this is lego_catalogue.nearest_colour. This is the same
    weighting vectorised, because the palette work below runs it over the whole
    grid several times and the per-cell Python version was the slowest step in
    the pipeline.
    """
    s = samples[:, None, :].astype(np.float32)
    p = palette[None, :, :].astype(np.float32)
    rmean = (s[..., 0] + p[..., 0]) / 2
    d = s - p
    return (
        (2 + rmean / 256) * d[..., 0] ** 2
        + 4 * d[..., 1] ** 2
        + (2 + (255 - rmean) / 256) * d[..., 2] ** 2
    )


def _choose_palette(
    samples: np.ndarray, max_colours: int, weights: np.ndarray | None = None
) -> list[int]:
    """Pick the colours this model is allowed to use, by clustering its own cells.

    Cluster first, snap second. The obvious alternative — snap every cell to its
    nearest colour and keep whichever came up most often — throws away exactly the
    colours that carry a building: the dark band of windows on a pale tower is a
    few percent of the cells and all of the detail, while a dozen near-identical
    greys survive on volume alone.

    Farthest-point initialisation rather than random, so the same photo produces
    the same palette every time. A parts list that changed between two runs of the
    same upload would be impossible to shop for.

    `weights` lets some cells pull harder on the clustering. Unweighted, a large
    plain wall dominates the sample count and the clusters settle on its half-dozen
    shades of the same stone, so a tower with the building's only real colour in it
    gets merged into the nearest grey. Weighting is how "spend the budget where it
    shows" is actually expressed here: the stud pitch is physical and cannot vary
    across one model, so resolution cannot be allocated regionally — the palette
    can.
    """
    k = min(max_colours, len(samples))
    centres = samples[np.argmin(((samples - samples.mean(0)) ** 2).sum(1))][None, :].copy()
    while len(centres) < k:
        far = samples[np.argmax(_redmean(samples, centres).min(axis=1))]
        centres = np.vstack([centres, far])

    w = np.ones(len(samples), dtype=np.float32) if weights is None else weights.astype(np.float32)
    for _ in range(_KMEANS_ITERATIONS):
        assign = _redmean(samples, centres).argmin(axis=1)
        moved = False
        for i in range(k):
            sel = assign == i
            if sel.any() and w[sel].sum() > 0:
                centre = (samples[sel] * w[sel, None]).sum(axis=0) / w[sel].sum()
                if not np.allclose(centre, centres[i]):
                    centres[i] = centre
                    moved = True
        if not moved:
            break

    lego = np.array([c.rgb for c in cat.COLOURS], dtype=np.float32)
    ids = [cat.COLOURS[i].colour_id for i in _redmean(centres, lego).argmin(axis=1)]
    # Two clusters can land on the same real colour; dict.fromkeys dedupes while
    # keeping the order, so the palette stays deterministic.
    return list(dict.fromkeys(ids))


def _smooth(
    rgb: np.ndarray, cells: np.ndarray, protect: np.ndarray | None = None
) -> np.ndarray:
    """Median-filter the cell grid before any colour decision is made.

    Averaging a cell's worth of pixels does not remove a photo's variation, it
    only shrinks it — a stone wall still arrives as cells that wobble either side
    of the boundary between two LEGO colours, and quantising picks a different
    side for each one. The wall comes out mottled from a surface that is, to the
    eye, flat.

    Median rather than blur: it moves a cell to a value its neighbours actually
    have, so a real edge between two materials stays exactly where it was instead
    of smearing into a band of intermediate colour a stud wide.

    Background cells are flooded with the building's mean colour first. Left
    alone, the sky would leak across the silhouette and tint its outermost studs —
    the one part of the model whose colour the eye checks against the photo.
    """
    if not cells.any():
        return rgb
    flooded = rgb.copy()
    flooded[~cells] = rgb[cells].mean(axis=0).astype(np.uint8)
    filtered = np.asarray(
        Image.fromarray(flooded).filter(ImageFilter.MedianFilter(3)), dtype=np.uint8
    )
    if protect is not None:
        # The filter's whole job is to erase one- and two-cell variation, which is
        # also the size of a window mullion. Where a region has been marked as
        # carrying the picture, the original is kept: mottling there costs less
        # than losing the feature.
        filtered = np.where(protect[..., None], rgb, filtered)
    # Only inside: outside the silhouette nothing is built, and keeping the
    # original there means the renders still show the photo's real background.
    return np.where(cells[..., None], filtered, rgb)


def _quantise_colours(
    rgb: np.ndarray,
    cells: np.ndarray,
    max_colours: int = DEFAULT_MAX_COLOURS,
    detail_weight: np.ndarray | None = None,
    dither: float = 0.0,
) -> np.ndarray:
    """Map every cell to a colour ID, drawn from a palette of at most max_colours."""
    h, w, _ = rgb.shape
    protect = None if detail_weight is None else (detail_weight > 1.5) & cells
    rgb = _smooth(rgb, cells, protect)
    samples = rgb[cells].astype(np.float32)
    if not len(samples):
        return np.zeros((h, w), dtype=np.int32)

    weights = None if detail_weight is None else detail_weight[cells]
    ids = np.array(_choose_palette(samples, max_colours, weights), dtype=np.int32)
    palette = np.array([cat.COLOURS_BY_ID[int(i)].rgb for i in ids], dtype=np.float32)
    if dither > 0:
        return _dither(rgb, cells, ids, palette, dither)
    nearest = _redmean(rgb.reshape(-1, 3).astype(np.float32), palette).argmin(axis=1)
    return ids[nearest].reshape(h, w)


# Floyd-Steinberg weights, over the four not-yet-visited neighbours.
_FS = ((1, 0, 5 / 16), (1, -1, 3 / 16), (1, 1, 1 / 16), (0, 1, 7 / 16))


def _dither(
    rgb: np.ndarray,
    cells: np.ndarray,
    ids: np.ndarray,
    palette: np.ndarray,
    strength: float,
) -> np.ndarray:
    """Map to the palette by error diffusion instead of by nearest colour.

    Snapping each cell independently is what leaves a sky or a lit wall in bands:
    a smooth ramp crosses the boundary between two palette entries once, and every
    cell on each side takes the same colour, so a gradient becomes two flat
    regions with a hard edge. Diffusion carries each cell's rounding error into
    the cells not yet decided, and the two colours interleave across the ramp in
    the proportion the original demanded.

    Whether that is an improvement depends on the photograph, which is why
    `strength` is a search parameter rather than a constant. On a facade of flat
    stone it adds noise to a surface that had none; on a dusk sky it is the
    difference between a horizon line and a sky. The score decides, per photo.

    Serpentine — alternate rows run right to left — because a single scan
    direction lets the error march steadily one way and leaves a diagonal grain
    that is quite visible once it is made of bricks.
    """
    h, w, _ = rgb.shape
    work = rgb.astype(np.float64).copy()
    out = np.zeros((h, w), dtype=np.int32)
    for y in range(h):
        xs = range(w) if y % 2 == 0 else range(w - 1, -1, -1)
        flip = 1 if y % 2 == 0 else -1
        for x in xs:
            if not cells[y, x]:
                continue
            pixel = np.clip(work[y, x], 0, 255)
            k = int(_redmean(pixel[None, :].astype(np.float32), palette).argmin())
            out[y, x] = ids[k]
            error = (pixel - palette[k]) * strength
            for dy, dx, weight in _FS:
                ny, nx = y + dy, x + dx * flip
                if 0 <= ny < h and 0 <= nx < w and cells[ny, nx]:
                    work[ny, nx] += error * weight
    return out


def _despeckle(colours: np.ndarray, cells: np.ndarray) -> np.ndarray:
    """Absorb single studs whose colour appears nowhere around them.

    A brick of a colour that none of its eight neighbours share is the photo's
    noise, not the building's, and at one stud across it reads as dirt on the
    wall. Replacing it with the commonest colour around it costs nothing, because
    there was no feature there to lose.

    The test is deliberately "appears nowhere", not "is in the minority". Real
    one-stud-wide features — a mullion, a downpipe, the shadowed edge of a
    pilaster — run for several courses, so every cell in them has at least one
    neighbour that agrees and none of them are touched.
    """
    h, w = colours.shape
    out = colours.copy()
    for y in range(h):
        for x in range(w):
            if not cells[y, x]:
                continue
            neighbours = [
                int(colours[ny, nx])
                for ny in range(max(0, y - 1), min(h, y + 2))
                for nx in range(max(0, x - 1), min(w, x + 2))
                if (ny, nx) != (y, x) and cells[ny, nx]
            ]
            if neighbours and int(colours[y, x]) not in neighbours:
                out[y, x] = Counter(neighbours).most_common(1)[0][0]
    return out


def _steady_depth(depth01: np.ndarray, cells: np.ndarray) -> np.ndarray:
    """Median-filter the depth field before it is quantised into layers.

    The facade skin is one stud thick, so a brick at depth 4 rests on whatever
    happens to be at depth 4 in the course below — and on nothing at all if that
    course quantised to 3. A monocular depth estimate wobbles by a few percent
    from cell to cell, which at five layers is enough to cross a layer boundary
    and back, and every crossing leaves a run of skin cantilevered over air.

    That is where the unsupported spans came from, and why there were three times
    as many at 128 studs as at 64: the finer the grid, the more often the estimate
    crosses a boundary. Smoothing the field costs a little relief accuracy in
    exchange for a facade that steps deliberately rather than jitters, and the
    steps that remain are the ones the building actually has.
    """
    if not cells.any():
        return depth01
    flooded = np.where(cells, depth01, float(depth01[cells].mean())).astype(np.float32)
    # A median over the 8-neighbourhood, done by sorting the stack of shifts:
    # PIL's median filter is 8-bit only, and rounding a depth field to 256 levels
    # before deciding which of five layers it lands in throws away the precision
    # the decision needs.
    stack = np.stack(
        [np.roll(np.roll(flooded, dy, axis=0), dx, axis=1)
         for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
    )
    smoothed = np.median(stack, axis=0)
    return np.where(cells, smoothed, depth01)


def _depths(depth01: np.ndarray, cells: np.ndarray, relief: int) -> np.ndarray:
    """How many studs deep each cell is: 1..relief inside the building, 0 outside.

    The facade of a cell with depth d sits at z = d - 1, so a larger value means
    nearer the viewer. Depth 0 means no brick at all, which is what makes the
    model the shape of the building rather than a box with a building on it.
    """
    depth01 = _steady_depth(depth01, cells)
    depths = np.clip((depth01 * relief).astype(np.int32) + 1, 1, relief)
    depths[~cells] = 0
    return depths


def _corbel(depths: np.ndarray) -> np.ndarray:
    """Make every course at least as deep as the one above it, per column.

    Where a facade steps *forward* as it rises, the skin at the top of the step
    has nothing beneath it — the course below stopped a stud short. That is the
    single source of the unsupported runs this model kept reporting, and it is not
    a measurement artefact: brick over air is brick over air, and it scales with
    resolution because a finer grid crosses more depth boundaries.

    Masonry has an answer, which is to corbel — build the lower courses out to
    meet what they carry. Propagating each column's depth downward does exactly
    that. It costs pieces and it thickens the massing below an overhang, so it is
    not obviously right for every subject; whether the trade is worth it is left
    to the score.
    """
    out = depths.copy()
    for y in range(depths.shape[0] - 2, -1, -1):
        carry = np.maximum(out[y], out[y + 1])
        # Only where the column is built at all — an empty cell must stay empty or
        # the silhouette grows a solid block under every overhang.
        out[y] = np.where(out[y] > 0, carry, 0)
    return out


# ---------------------------------------------------------------- glazing


# A window is darker than the wall around it, and it is small. Both halves of that
# matter. Darkness alone glazes the entire shadowed side of a building; size alone
# glazes every patch of dark stone. Together they pick out openings.
GLAZING_DARKNESS = 0.74  # at most this share of the surrounding wall's luminance
GLAZING_MIN_CELLS = 2  # one cell on its own is noise, not a window
GLAZING_MAX_CELLS = 30  # larger than this is a shadow or a doorway-sized void
_GLAZING_NEIGHBOURHOOD = 4  # radius, in studs, of "the wall around it"


def _box_mean(a: np.ndarray, r: int) -> np.ndarray:
    """Mean over each (2r+1)-square, edges replicated.

    Rolled by hand rather than through PIL: ImageFilter.BoxBlur refuses mode "F",
    and routing a luminance field through uint8 to get around that quantises the
    very differences this is measuring.
    """
    k = 2 * r + 1
    h, w = a.shape
    padded = np.pad(a.astype(np.float64), r, mode="edge")
    cs = np.pad(np.cumsum(np.cumsum(padded, axis=0), axis=1), ((1, 0), (1, 0)))
    total = cs[k : k + h, k : k + w] - cs[0:h, k : k + w] - cs[k : k + h, 0:w] + cs[0:h, 0:w]
    return (total / (k * k)).astype(np.float32)


def _blobs(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    """Four-connected components of a boolean grid, as lists of coordinates."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out: list[list[tuple[int, int]]] = []
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            stack, blob = [(y, x)], []
            seen[y, x] = True
            while stack:
                cy, cx = stack.pop()
                blob.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            out.append(blob)
    return out


def _windows(rgb: np.ndarray, cells: np.ndarray) -> np.ndarray:
    """Which cells to build in glass rather than stone.

    Measured against the *local* wall rather than a global threshold, because a
    building is not evenly lit: the windows on the sunlit face can be brighter
    than the stone on the shaded one, and any single cutoff either glazes a whole
    elevation or misses it entirely.

    Runs on the raw sampled grid, before the median filter in _quantise_colours.
    That filter exists to remove one- and two-cell features, and at ninety-six
    studs across a landmark most windows are exactly that size — detecting them
    afterwards would find nothing.
    """
    if not cells.any():
        return np.zeros_like(cells)

    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float32)
    # Flood the background with the building's own mean before blurring, so the
    # sky does not drag the local wall level down and glaze the whole skyline.
    flooded = np.where(cells, lum, float(lum[cells].mean())).astype(np.float32)
    wall = _box_mean(flooded, _GLAZING_NEIGHBOURHOOD)

    dark = cells & (lum < wall * GLAZING_DARKNESS)
    out = np.zeros_like(cells)
    for blob in _blobs(dark):
        if GLAZING_MIN_CELLS <= len(blob) <= GLAZING_MAX_CELLS:
            for y, x in blob:
                out[y, x] = True
    return out


# ---------------------------------------------------------------- partitioning


# An enclosed gap smaller than this share of the building is not a feature of the
# building. Tower Bridge's arch is 6% of its silhouette and survives; the gaps a
# bare branch punches across a facade are a fraction of a percent.
HOLE_MAX_SHARE = 0.02


def _fill_occlusions(cells: np.ndarray) -> tuple[np.ndarray, int]:
    """Close small enclosed gaps in the silhouette.

    The segmenter is asked which pixels are building, and it answers correctly:
    where a bare branch crosses the facade, those pixels are tree. The result is a
    mask with the building's own shape perforated, and every brick above one of
    those perforations has nothing beneath it. That, and not the depth quantising,
    was where most of the unsupported runs came from on a photograph taken through
    winter trees — corbelling the depth field did not touch them, because the
    problem was never depth.

    Only *enclosed* gaps, and only small ones. A gap that reaches the edge of the
    frame is the sky beside the building, and a large enclosed one is something
    you can genuinely see through — the arch of a bridge, a gateway, the space
    between two towers. Filling those would weld the building into a slab.
    """
    h, w = cells.shape
    empty = ~cells
    # Flood from the border: whatever it reaches is outside, not a hole.
    outside = np.zeros_like(empty)
    stack = [(y, x) for y in range(h) for x in (0, w - 1) if empty[y, x]]
    stack += [(y, x) for x in range(w) for y in (0, h - 1) if empty[y, x]]
    for y, x in stack:
        outside[y, x] = True
    while stack:
        y, x = stack.pop()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and empty[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                stack.append((ny, nx))

    building = max(1, int(cells.sum()))
    limit = building * HOLE_MAX_SHARE
    filled = cells.copy()
    closed = 0
    seen = outside.copy()
    for sy in range(h):
        for sx in range(w):
            if not empty[sy, sx] or seen[sy, sx]:
                continue
            blob, stack2 = [], [(sy, sx)]
            seen[sy, sx] = True
            while stack2:
                y, x = stack2.pop()
                blob.append((y, x))
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if (0 <= ny < h and 0 <= nx < w and empty[ny, nx] and not seen[ny, nx]):
                        seen[ny, nx] = True
                        stack2.append((ny, nx))
            if len(blob) <= limit:
                for y, x in blob:
                    filled[y, x] = True
                closed += len(blob)
    return filled, closed


def _ground(depths: np.ndarray) -> np.ndarray:
    """Carry every column down to the floor.

    Measured, after guessing wrong twice about where the unsupported runs came
    from. They are not depth steps and not gaps punched by branches: the longest
    of them sit at courses one and two, and the course beneath is empty across
    twenty studs. Whole sections of the building were starting a course or two
    above the plate floor and standing on nothing.

    The reason is in the photograph. Snow banked against the steps, a hedge, the
    shadow under a porch — the segmenter is right that those pixels are not
    building, and the consequence is a silhouette with a ragged bottom edge. A
    building does not have a ragged bottom edge; it meets the ground.

    Each column is extended down at the depth of its own lowest brick, so the base
    keeps the massing it was given rather than being squared off to the deepest
    part of the facade.
    """
    out = depths.copy()
    courses, width = depths.shape
    for x in range(width):
        column = np.nonzero(out[:, x])[0]
        if not len(column):
            continue
        base = int(column[0])
        if base:
            out[:base, x] = out[base, x]
    return out


def _standing(depths: np.ndarray) -> tuple[np.ndarray, int]:
    """Delete everything that does not reach the floor.

    A connectivity check, and the reason it is worth doing is that it is the only
    stability test that costs nothing. The literature's stronger option is a
    force-balance linear program (Legolization, SIGGRAPH Asia 2015; BrickGPT,
    ICCV 2025) — BrickGPT needs a Gurobi licence for it and falls back to exactly
    this connectivity rule without one. Connectivity will not tell you a wall is
    too thin, but it does catch the thing that is actually wrong here: a lamp
    post, or a tree branch crossing in front of the building, gets segmented as
    part of the subject and comes out as a lump of brick hanging in mid-air.

    The mask cleaner upstream keeps any blob above half a percent of the total,
    which is a size test, not a physics one — a lamp post clears it comfortably.
    Reaching the ground is the test that matters, because a model is a thing that
    has to stand on a table.

    Returns the pruned depth grid and how many cells were dropped.
    """
    courses, width = depths.shape
    solid = depths > 0
    if not solid.any():
        return depths, 0

    keep = np.zeros_like(solid)
    seen = np.zeros_like(solid)
    # Seed from the lowest course that has anything in it, not from course 0.
    # Course 0 is often empty: the crop is to the mask's bounding box in pixels,
    # and the bottom row of studs then fails the half-coverage test that decides
    # whether a cell counts as building. Seeding from course 0 found no seeds at
    # all and deleted the entire model — 36 pieces came out, every one of them
    # floor, and every internal check passed, because an empty building is
    # perfectly self-consistent.
    base = int(np.argmax(solid.any(axis=1)))
    stack = [(base, x) for x in range(width) if solid[base, x]]
    for y, x in stack:
        seen[y, x] = True
    while stack:
        y, x = stack.pop()
        keep[y, x] = True
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < courses and 0 <= nx < width and solid[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                stack.append((ny, nx))

    # Reaching the ground is necessary but not sufficient. A street lamp in front
    # of the building stands on the ground too, so connectivity alone keeps it —
    # it survived the first version of this and is the speck still floating at the
    # left of the render. The subject of a photograph is one object; anything
    # standing apart from the main mass is something else that happened to be in
    # frame.
    kept_labels, sizes = [], []
    seen2 = np.zeros_like(keep)
    for sy in range(courses):
        for sx in range(width):
            if not keep[sy, sx] or seen2[sy, sx]:
                continue
            comp, stack2 = [], [(sy, sx)]
            seen2[sy, sx] = True
            while stack2:
                y, x = stack2.pop()
                comp.append((y, x))
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if (0 <= ny < courses and 0 <= nx < width
                            and keep[ny, nx] and not seen2[ny, nx]):
                        seen2[ny, nx] = True
                        stack2.append((ny, nx))
            kept_labels.append(comp)
            sizes.append(len(comp))
    if sizes:
        biggest = max(sizes)
        for comp, size in zip(kept_labels, sizes):
            if size < biggest * SUBJECT_MIN_SHARE:
                for y, x in comp:
                    keep[y, x] = False

    dropped = int(solid.sum() - keep.sum())
    if dropped:
        logger.info("Dropped %d cells that never reached the floor", dropped)
    out = depths.copy()
    out[~keep] = 0
    return out, dropped


def _partition(mask: np.ndarray, catalogue: list[cat.Plate]) -> list[tuple[int, int, cat.Plate]]:
    """Cover a boolean grid with the fewest bricks a greedy pass can manage.

    Scans row-major and, at each uncovered cell, drops in the largest catalogue
    brick that fits entirely inside the mask — trying both orientations, since a
    2x4 and a 4x2 are the same part. Optimal rectangle covering is NP-hard;
    largest-first greedy lands within a few percent and runs instantly.

    Returns (column, row, brick) with the brick's `width` along the columns.
    """
    rows, cols = mask.shape
    covered = np.zeros_like(mask, dtype=bool)
    out: list[tuple[int, int, cat.Plate]] = []

    for r in range(rows):
        for c in range(cols):
            if not mask[r, c] or covered[r, c]:
                continue
            for brick in catalogue:
                placed = False
                for bw, bl in {(brick.width, brick.length), (brick.length, brick.width)}:
                    if c + bw > cols or r + bl > rows:
                        continue
                    window = mask[r : r + bl, c : c + bw]
                    if window.all() and not covered[r : r + bl, c : c + bw].any():
                        covered[r : r + bl, c : c + bw] = True
                        # _replace, not a fresh Plate: rebuilding one positionally
                        # drops every field after `length`, which since tiles
                        # joined the catalogue means silently turning an 8 LDU
                        # part back into a 24 LDU one.
                        out.append((c, r, brick._replace(width=bw, length=bl)))
                        placed = True
                        break
                if placed:
                    break
    return out


def _course_cells(
    depths: np.ndarray, colours: np.ndarray, y: int, relief: int, reserved: np.ndarray
) -> list[Cell]:
    """Every brick in one course.

    Split in two: the facade skin, which is one stud deep so that no brick ever
    spans two colours of the picture, and the fill behind it, which is hidden and
    therefore all one colour and free to use the widest parts in the catalogue.
    """
    row_depth = depths[y]
    result: list[Cell] = []

    # --- skin: the cells you can see, at z = depth - 1, grouped by colour ---
    for colour_id in np.unique(colours[y][row_depth > 0]):
        for d in np.unique(row_depth[row_depth > 0]):
            strip = (row_depth == d) & (colours[y] == colour_id) & ~reserved[y]
            if not strip.any():
                continue
            for x, _, brick in _partition(strip[np.newaxis, :], cat.SKIN_BRICKS):
                result.append(Cell(x, y, int(d) - 1, brick, int(colour_id), hidden=False))

    # --- fill: everything between the back plane and the skin ---
    # Laid out in the (z, x) plane so a single 2x4 can span two layers of depth.
    fill = np.zeros((relief, len(row_depth)), dtype=bool)
    for z in range(relief):
        # ~reserved: a roof slope spans its column's full depth, so the fill it
        # replaced must not be laid as well — that is what left a grey step
        # standing beside every slope the first time round.
        fill[z] = (row_depth > z + 1) & ~reserved[y]
    if fill.any():
        for x, z, brick in _partition(fill, cat.BRICKS_BY_AREA):
            result.append(Cell(x, y, z, brick, cat.FILL_COLOUR_ID, hidden=True))

    return result


# The roofline slopes, and why only these two.
#
# LEGO's angle names describe a run and a rise, and the community's roofing guides
# and the measured geometry agree: the 45° family covers two studs of run per
# course of rise, the 33° family three. Before slope parts existed, a pitched roof
# was built by setting each course back one stud — which is exactly the staircase
# a photograph's silhouette produces here, so the substitution is direct.
#
# Both parts are one stud deep, which is what the facade skin is. A "Slope 45 2x2"
# would be two studs deep and would push through the back of the skin into the
# fill, so the wider slopes in the library are no use for a roofline however
# common they are.
# Keyed by (run in studs, depth in studs). Depth matters as much as run: a slope
# only one stud deep caps the skin and leaves the fill behind it standing at full
# height, so the roof renders as a smooth face with a grey step poking through
# beside every piece. The part has to be as deep as the facade is at that column.
ROOF_SLOPES: dict[tuple[int, int], str] = {
    (2, 1): "3040b",  # Brick Sloped 45 degrees, 2 x 1
    (2, 2): "3039",
    (2, 3): "3038",
    (2, 4): "3037",
    (3, 1): "4286",   # Brick Sloped 33 degrees, 3 x 1
    (3, 2): "3298",
}

# Longest run first, so a gentle step gets the 33 degree part and a sharp one
# falls back to the 45.
ROOF_RUNS: tuple[int, ...] = (3, 2)


def _roofline(depths: np.ndarray, colours: np.ndarray) -> tuple[list[Cell], np.ndarray]:
    """Replace one-course steps in the silhouette with slope bricks.

    Returns the slopes and a mask of the cells they occupy, so the ordinary skin
    partition can leave those cells alone. A slope takes the place of the top
    course brick rather than sitting on top of it: it *is* that course, which is
    why it changes nothing about the model's height or its coverage.

    Longer runs are tried first, so a gentle step gets the 33° part and a sharp
    one falls back to the 45°.
    """
    courses, width = depths.shape
    reserved = np.zeros((courses, width), dtype=bool)
    tops = [
        int(np.max(np.nonzero(depths[:, x])[0])) if depths[:, x].any() else -1
        for x in range(width)
    ]
    out: list[Cell] = []

    def uniform(lo: int, hi: int) -> bool:
        """Whether columns lo..hi-1 share a top course and a facade depth."""
        if lo < 0 or hi > width:
            return False
        y = tops[lo]
        if y < 0:
            return False
        d = depths[y, lo]
        return all(
            tops[x] == y and depths[y, x] == d and not reserved[y, x]
            for x in range(lo, hi)
        )

    for run in ROOF_RUNS:
        for x in range(width - 1):
            here, right = tops[x], tops[x + 1]
            if here < 0 or right < 0:
                continue
            # Descending to the right: the slope goes on the higher side, ending
            # at this column, and falls away toward +x.
            if here - right == 1 and uniform(x - run + 1, x + 1):
                part_num = ROOF_SLOPES.get((run, int(depths[here, x])))
                if not part_num:
                    continue  # no slope that deep exists; leave the staircase
                shape = shapes.BY_PART[part_num]
                out.append(Cell(x - run + 1, here, 0,
                                cat.Plate(part_num, shape.name, run, shape.width),
                                int(colours[here, x]), hidden=False, rot="y90"))
                reserved[here, x - run + 1 : x + 1] = True
            # Ascending to the right: the higher side starts at x+1.
            elif right - here == 1 and uniform(x + 1, x + 1 + run):
                part_num = ROOF_SLOPES.get((run, int(depths[right, x + 1])))
                if not part_num:
                    continue
                shape = shapes.BY_PART[part_num]
                out.append(Cell(x + 1, right, 0,
                                cat.Plate(part_num, shape.name, run, shape.width),
                                int(colours[right, x + 1]), hidden=False, rot="y270"))
                reserved[right, x + 1 : x + 1 + run] = True
    return out, reserved


def _coping(depths: np.ndarray, colours: np.ndarray, reserved: np.ndarray) -> list[Cell]:
    """Tiles over every exposed top edge of the facade.

    A wall built only of bricks ends in a row of bare studs pointing at the sky,
    and a stepped silhouette has one of those rows at every step. That row is the
    strongest single cue that what you are looking at is a toy: real buildings end
    in coping stones, parapets and copings, all of them flat. A tile is the part
    that says "this edge is finished", and it is what a builder would reach for.

    Only the skin is capped. The fill behind it is never seen from any angle the
    model is meant to be looked at, and tiling it would add hundreds of pieces to
    hide studs nobody can see.
    """
    courses, width = depths.shape
    tiles: list[Cell] = []
    # Group by (course, depth) so one run of tiles never straddles a step.
    runs: dict[tuple[int, int], np.ndarray] = {}
    for y in range(courses):
        # A slope already finishes its own top edge; tiling over one would bury
        # the shape that was the whole point of placing it.
        exposed = (depths[y] > 0) & ~reserved[y] & (
            np.ones(width, dtype=bool) if y + 1 == courses else depths[y + 1] == 0
        )
        if not exposed.any():
            continue
        for d in np.unique(depths[y][exposed]):
            runs[(y, int(d) - 1)] = exposed & (depths[y] == d)

    for (y, z), strip in runs.items():
        for colour_id in np.unique(colours[y][strip]):
            band = strip & (colours[y] == colour_id)
            if not band.any():
                continue
            for x, _, tile in _partition(band[np.newaxis, :], cat.TILES_BY_AREA):
                tiles.append(Cell(x, y, z, tile, int(colour_id), hidden=False, cap=True))
    return tiles


def _build(depths: np.ndarray, colours: np.ndarray, relief: int) -> list[Cell]:
    courses = depths.shape[0]
    # Slopes are chosen first because they claim cells the skin would otherwise
    # fill with ordinary bricks; everything after works around what they took.
    slopes, reserved = _roofline(depths, colours)
    cells: list[Cell] = list(slopes)
    for y in range(courses):
        cells.extend(_course_cells(depths, colours, y, relief, reserved))
    return cells + _coping(depths, colours, reserved)


# ---------------------------------------------------------------- checks


# A run of bricks with nothing beneath it but solid material at both ends is a
# lintel, and LEGO walls are full of them — every window has one. Past roughly this
# width a course of plain bricks sags and eventually pops apart under its own
# weight, and the builder needs a plate spanning the joint or a beam behind it.
SAFE_LINTEL_STUDS = 8


def _support(cells: list[Cell], depths: np.ndarray, relief: int) -> dict[str, Any]:
    """Find the parts of the model that will not hold themselves up.

    Nothing here fixes anything — it measures, so the numbers can be reported
    instead of assumed. Course 0 sits on the floor and is supported by
    definition.

    Three outcomes, which are not the same problem:

      overhang  a stud or two past the course below. Normal; friction and
                staggered joints carry it, and every LEGO wall does this.
      lintel    a longer run with nothing beneath but solid brick at both ends,
                like the course above a window. Sound up to a span, then not.
      floating  nothing beneath and no anchor either side. Not buildable at all;
                this is a piece of the picture hanging in mid-air.
    """
    courses, width = depths.shape
    occupied = np.zeros((courses, relief, width), dtype=bool)
    for y in range(courses):
        for z in range(relief):
            occupied[y, z] = depths[y] > z

    overhangs = lintels = floating = wide_lintels = 0
    longest_lintel = 0
    longest_floating = 0

    for y in range(1, courses):
        for z in range(relief):
            here, below = occupied[y, z], occupied[y - 1, z]
            x = 0
            while x < width:
                if not (here[x] and not below[x]):
                    x += 1
                    continue
                start = x
                while x < width and here[x] and not below[x]:
                    x += 1
                span = x - start
                # Anchored when the cell just outside the run exists and is itself
                # standing on something.
                left = start > 0 and here[start - 1] and below[start - 1]
                right = x < width and here[x] and below[x]
                if span <= 2:
                    overhangs += 1
                elif left and right:
                    lintels += 1
                    longest_lintel = max(longest_lintel, span)
                    if span > SAFE_LINTEL_STUDS:
                        wide_lintels += 1
                else:
                    floating += 1
                    longest_floating = max(longest_floating, span)

    return {
        "overhangs": overhangs,
        "lintels": lintels,
        "longestLintelStuds": longest_lintel,
        "floatingRuns": floating,
        "longestFloatingStuds": longest_floating,
        # The one number worth acting on: spans a builder has to reinforce.
        "spansNeedingSupport": wide_lintels + floating,
        "sound": floating == 0 and wide_lintels == 0,
    }


def _check(cells: list[Cell], depths: np.ndarray, relief: int) -> None:
    """Invariants that must hold for the plan to mean anything. Cheap; always on."""
    courses, width = depths.shape
    filled = np.zeros((courses, relief, width), dtype=np.int32)
    for c in cells:
        if c.y == FLOOR or c.cap:
            continue
        filled[c.y, c.z : c.z + c.brick.length, c.x : c.x + c.brick.width] += 1

    want = np.zeros_like(filled, dtype=bool)
    for y in range(courses):
        for z in range(relief):
            want[y, z] = depths[y] > z

    if (filled > 1).any():
        raise AssertionError(f"{int((filled > 1).sum())} cells covered by two bricks")
    if (filled[~want] != 0).any():
        raise AssertionError("bricks placed outside the building")
    if (filled[want] == 0).any():
        raise AssertionError(f"{int((filled[want] == 0).sum())} building cells left empty")


# ---------------------------------------------------------------- output


def _tally(cells: list[Cell]) -> list[dict[str, Any]]:
    """Roll the model up into a shopping list keyed by (part, colour, visibility).

    Visibility is part of the key so a visible Light Bluish Gray brick is not
    quietly merged into the hidden fill order, which uses the same colour.
    """
    counts: Counter[tuple[str, str, int, bool]] = Counter()
    for c in cells:
        counts[(c.brick.part_num, c.brick.name, c.colour_id, c.hidden)] += 1

    out: list[dict[str, Any]] = []
    for (part_num, name, colour_id, hidden), qty in counts.items():
        colour = cat.COLOURS_BY_ID[colour_id]
        out.append(
            {
                "name": name,
                "partId": part_num,
                "color": colour.name,
                "colorId": colour_id,
                "colorHex": colour.hex,
                "quantity": qty,
                "hidden": hidden,
                "description": "Structure behind the facade" if hidden else "Facade",
            }
        )
    # Biggest orders first — that is the order you would pick them in.
    out.sort(key=lambda b: (-b["quantity"], b["partId"]))
    return out


def _summarise(cells: list[Cell]) -> list[str]:
    """Human-readable 'Part (Colour) xN' lines for one build step."""
    counts: Counter[tuple[str, str]] = Counter()
    for c in cells:
        counts[(c.brick.name, cat.COLOURS_BY_ID[c.colour_id].name)] += 1
    return [
        f"{name} ({colour}) x{qty}"
        for (name, colour), qty in sorted(counts.items(), key=lambda kv: -kv[1])
    ]


# Courses per step. One step per course would be 40 steps of two minutes each;
# bands of this many read like a real instruction booklet.
COURSES_PER_STEP = 6


def _assembly_steps(
    cells: list[Cell], courses: int, floor: list[Cell]
) -> list[dict[str, Any]]:
    """Bottom-up bands of courses — the order you would actually build in."""
    steps: list[dict[str, Any]] = [
        {
            "step": 1,
            "title": "Floor",
            "description": (
                f"Lay {len(floor)} plates into a solid rectangle. The model is built "
                f"standing up: stud (0,0) is the back-left corner of the floor, and the "
                f"facade grows toward you as the courses rise."
            ),
            "bricksUsed": _summarise(floor),
        }
    ]
    for start in range(0, courses, COURSES_PER_STEP):
        end = min(start + COURSES_PER_STEP, courses)
        band = [c for c in cells if start <= c.y < end]  # FLOOR is negative, so excluded
        if not band:
            continue
        visible = [c for c in band if not c.hidden]
        hidden = [c for c in band if c.hidden]
        steps.append(
            {
                "step": len(steps) + 1,
                # Kept so callers can align per-band commentary with the right
                # step; step numbers shift when an empty band is skipped.
                "level": start // COURSES_PER_STEP + 1,
                "title": (
                    f"Courses {start + 1}–{end} of {courses}"
                    if end > start + 1
                    else f"Course {end} of {courses}"
                ),
                "description": (
                    f"Lay {len(hidden)} bricks of backing, then face them with the "
                    f"{len(visible)} coloured bricks that make up this band of the "
                    f"picture. Stagger the joints against the course below."
                ),
                "bricksUsed": _summarise(band),
                "tip": (
                    "Work back to front: the backing sets the depth each facade brick "
                    "sits at, and a facade brick one stud out of place is visible from "
                    "across the room."
                    if hidden
                    else None
                ),
            }
        )
    for s in steps:
        if s.get("tip") is None:
            s.pop("tip", None)
    return steps


# What the search tries. Small and explicit rather than a continuous optimiser:
# these are the three settings that actually move the score, the grid is cheap
# enough to enumerate, and an enumerated grid can be printed in a log and argued
# with. The candidates are not free of judgement — 160 studs is omitted because
# the piece count stops being something a person would buy — but the *choice*
# between them is made by measurement instead of by a default.
SEARCH_STUDS: tuple[int, ...] = (64, 96, 128)
SEARCH_RELIEF: tuple[int, ...] = (3, 5)
SEARCH_COLOURS: tuple[int, ...] = (8, 12, 16)
# Whether to diffuse the quantisation error, and how hard. Dithering is not an
# improvement in general — it trades per-cell colour accuracy for local-average
# accuracy, which is worth it on a dusk sky and a waste on flat stone. Neither
# guess survives contact with a particular photograph, so both are offered.
SEARCH_DITHER: tuple[float, ...] = (0.0, 0.6)
# Corbelling costs pieces and thickens the massing under an overhang. It earns
# that back on a subject with real spans and does nothing on one without.
SEARCH_CORBEL: tuple[bool, ...] = (False, True)


def generate_best_plan(
    image: bytes | Image.Image,
    depth_map: np.ndarray,
    building_mask: np.ndarray | None = None,
    candidates: int | None = None,
) -> dict[str, Any]:
    """Build the model several ways and keep the one that looks most like the photo.

    This is the loop the pipeline did not have. It used to build once, at fixed
    settings, and ship whatever came out — so a night photograph came back as a
    navy lump and nothing anywhere knew that was worse than usual.

    The settings genuinely disagree between photographs, which is the argument for
    searching rather than tuning a default: Altgeld Hall scores best at five studs
    of relief and a landmark elevation like Tower Bridge scores best at three,
    because one is a massed building shot at an angle and the other is close to a
    flat facade. A single default is wrong for one of them whichever way it is set.

    One plan costs about fifty milliseconds at these sizes; depth estimation and
    segmentation, which run once and are shared by every candidate, cost twenty
    seconds. The search is therefore free in the only sense that matters.
    """
    if isinstance(image, bytes):
        import io

        image = Image.open(io.BytesIO(image))

    tried: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    for studs in SEARCH_STUDS:
        for relief in SEARCH_RELIEF:
            for ncol in SEARCH_COLOURS:
                for dither in SEARCH_DITHER:
                    for corbel in SEARCH_CORBEL:
                        if candidates is not None and len(tried) >= candidates:
                            break
                        plan = generate_plan(
                            image, depth_map, building_mask=building_mask,
                            max_studs=studs, relief_studs=relief, max_colours=ncol,
                            dither=dither, corbel=corbel,
                        )
                        tried.append({
                            "studs": studs, "relief": relief, "colours": ncol,
                            "dither": dither, "corbel": corbel,
                            "overall": plan["fidelity"]["overall"],
                            "pieces": plan["estimatedPieceCount"],
                        })
                        if best is None or plan["fidelity"]["overall"] > best["fidelity"]["overall"]:
                            best = plan

    assert best is not None
    tried.sort(key=lambda t: -t["overall"])
    best["search"] = {
        "tried": len(tried),
        "chosen": {k: tried[0][k] for k in ("studs", "relief", "colours", "dither", "corbel")},
        # The runners-up, so a result that looks wrong can be argued with rather
        # than only accepted: if the second choice scored 0.599 against 0.601, the
        # search did not really decide anything and the score needs work.
        "ranking": tried[:5],
    }
    logger.info(
        "Searched %d builds; chose %s at %.3f",
        len(tried), best["search"]["chosen"], tried[0]["overall"],
    )
    return best


# How many of the worst tiles get the extra budget each round, and how much extra.
# Boosting everything is the same as boosting nothing — the weights only mean
# anything relative to each other.
REFINE_TILES = 5
REFINE_BOOST = 3.0
REFINE_ROUNDS = 3


def refine_plan(
    image: bytes | Image.Image,
    depth_map: np.ndarray,
    building_mask: np.ndarray | None = None,
    rounds: int = REFINE_ROUNDS,
) -> dict[str, Any]:
    """Search for settings, then spend the colour budget where the model is worst.

    The second half of the loop. The search picks a resolution, a relief and a
    palette size; this takes the winner and asks a different question — given
    those, *where* is it wrong, and can the same budget be spent better?

    What can and cannot be reallocated is set by the medium, and it is worth being
    precise about it. Resolution cannot: the stud pitch is twenty LDU everywhere in
    a real model, so "more detail on the tower" is not a thing that can be granted
    by making its cells smaller. What can be reallocated is the palette — which
    colours the dozen slots are spent on — and where the smoothing is allowed to
    erase small features. Both are aimed by the same weight grid.

    Every round is kept only if it scores better than what came before, so the
    result can never be worse than the search's own answer. A round that fails is
    reported rather than hidden: `refine.rounds` records what each one scored,
    which is the only way to tell "refinement helped" from "refinement ran".
    """
    if isinstance(image, bytes):
        import io

        image = Image.open(io.BytesIO(image))

    best = generate_best_plan(image, depth_map, building_mask=building_mask)
    chosen = best["search"]["chosen"]
    history = [{"round": 0, "overall": best["fidelity"]["overall"], "note": "search winner"}]

    weight = np.ones_like(best["_grids"]["mask"], dtype=np.float64)
    for r in range(1, rounds + 1):
        grids = best["_grids"]
        flat = np.array(
            [cat.COLOURS_BY_ID[int(c)].rgb for c in grids["colours"].ravel()], dtype=np.uint8
        ).reshape(*grids["colours"].shape, 3)
        both = grids["mask"] & (grids["depths"] > 0)
        worst = scoring.worst_regions(grids["source"], flat, both, tiles=6)[:REFINE_TILES]
        if not worst:
            break

        # Aim the next attempt at those tiles. Weights accumulate across rounds, so
        # a region that stays bad keeps gaining pull rather than being visited once.
        h, w = weight.shape
        ys = np.linspace(0, h, 7).astype(int)
        xs = np.linspace(0, w, 7).astype(int)
        for t in worst:
            weight[ys[t["row"]]:ys[t["row"] + 1], xs[t["col"]]:xs[t["col"] + 1]] *= REFINE_BOOST

        candidate = generate_plan(
            image, depth_map, building_mask=building_mask,
            max_studs=chosen["studs"], relief_studs=chosen["relief"],
            max_colours=chosen["colours"], dither=chosen["dither"],
            corbel=chosen["corbel"], detail_weight=weight,
        )
        better = candidate["fidelity"]["overall"] > best["fidelity"]["overall"]
        history.append({
            "round": r,
            "overall": candidate["fidelity"]["overall"],
            "worstTileDeltaE": worst[0]["colourDeltaE"],
            "kept": better,
        })
        if better:
            candidate["search"] = best["search"]
            best = candidate
        else:
            # Keep going: the weights accumulate, so a round that did not pay off
            # still moves the next one further in the same direction. Stopping at
            # the first failure would mistake a plateau for a peak.
            continue

    best["refine"] = {"rounds": history, "improved": round(
        history[-1]["overall"] - history[0]["overall"], 4) if len(history) > 1 else 0.0}
    logger.info("Refinement: %s", history)
    return best


def _fidelity(
    rgb: np.ndarray,
    colours: np.ndarray,
    depths: np.ndarray,
    cells_mask: np.ndarray,
    depth01: np.ndarray,
    cells: list[Cell],
    structure: dict | None = None,
    pieces: int | None = None,
    piece_budget: int = DEFAULT_PIECE_BUDGET,
) -> dict[str, float]:
    """Score the plan against the photo, comparing a lit render rather than a grid.

    The render is downsampled straight back to the stud grid. It is not there to
    be looked at — render_model at display scale is for that — but rendering and
    then reducing is not the same as never rendering: the shading, the contact
    shadows and the flat tops of the tiles all survive the reduction, and none of
    them exist in the raw colour grid.
    """
    flat = np.array(
        [cat.COLOURS_BY_ID[int(c)].rgb for c in colours.ravel()], dtype=np.uint8
    ).reshape(*colours.shape, 3)
    tiled = np.zeros_like(cells_mask)
    for c in cells:
        if c.cap:
            tiled[c.y, c.x : c.x + c.brick.width] = True
    lit = np.asarray(
        render_model(depths, colours, scale=4, tiled=tiled)
        .convert("RGB")
        .resize((depths.shape[1], depths.shape[0]), Image.Resampling.BOX),
        dtype=np.float64,
    )[::-1]  # render_model flips for display; the grids are ground-up
    return scoring.score(
        rgb, flat, cells_mask, depths > 0, depth01, depths, lit,
        structure=structure, pieces=pieces, piece_budget=piece_budget,
    )


def generate_plan(
    image_bytes_or_image: bytes | Image.Image,
    depth_map: np.ndarray,
    building_mask: np.ndarray | None = None,
    max_studs: int = DEFAULT_MAX_STUDS,
    relief_studs: int = DEFAULT_RELIEF_STUDS,
    max_colours: int = DEFAULT_MAX_COLOURS,
    glazing: bool = True,
    detail_weight: np.ndarray | None = None,
    dither: float = 0.0,
    corbel: bool = False,
    piece_budget: int = DEFAULT_PIECE_BUDGET,
) -> dict[str, Any]:
    """Produce a verified LEGO build plan from a photo and its depth map.

    Pass building_mask (same pixel dimensions as the image) to build only the
    building. Without one the whole frame is turned into bricks, sky included.
    """
    if isinstance(image_bytes_or_image, bytes):
        import io

        image = Image.open(io.BytesIO(image_bytes_or_image))
    else:
        image = image_bytes_or_image

    rgb, depth01, cells_mask, width, courses = _sample(
        image, depth_map, building_mask, max_studs
    )
    # Windows are found first, on the raw grid, because the smoothing inside
    # _quantise_colours is specifically designed to erase features this small.
    # They are painted on last, so neither the palette nor the despeckle can
    # decide a window was noise.
    glass = _windows(rgb, cells_mask) if glazing else np.zeros_like(cells_mask)
    colours = _quantise_colours(rgb, cells_mask, max_colours, detail_weight, dither)
    # Despeckling removes single cells whose colour no neighbour shares, which is
    # precisely the pattern diffusion produces on purpose. Running both would
    # spend the work on the dither and then undo it.
    if dither == 0:
        colours = _despeckle(colours, cells_mask)
    colours[glass] = cat.DEFAULT_GLAZING_ID
    depths = _depths(depth01, cells_mask, relief_studs)
    depths = _ground(depths)
    if corbel:
        depths = _corbel(depths)
    depths, orphaned = _standing(depths)

    cells = _floor(width, relief_studs, depths.any(axis=0)) + _build(depths, colours, relief_studs)
    _check(cells, depths, relief_studs)

    bricks = _tally(cells)
    floor = [c for c in cells if c.y == FLOOR]

    total_pieces = sum(b["quantity"] for b in bricks)
    visible = [b for b in bricks if not b["hidden"]]
    # Ordered by how much of the facade each colour accounts for, so the palette
    # reads as "this is mostly brown and grey" rather than as an alphabet.
    by_colour: Counter[int] = Counter()
    for b in visible:
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

    # Minutes per piece is a rough builder's rule of thumb. A standing build is
    # slower than a mosaic: every course has to be checked for depth as well as
    # colour, and the backing goes in before the face.
    # Computed here rather than inline below: the score needs it, and calling
    # _support twice would double the most expensive check in the pipeline.
    structure = _support(cells, depths, relief_studs)

    minutes = total_pieces * 0.16
    if total_pieces < 400:
        difficulty = "Beginner"
    elif total_pieces < 1400:
        difficulty = "Intermediate"
    else:
        difficulty = "Expert"

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
            "depthStuds": relief_studs,
        },
        "grid": {
            "width": width,
            "courses": courses,
            "depth": relief_studs,
            # Physical size, which is what someone deciding whether to build this
            # actually wants to know.
            "sizeCm": {
                "width": round(width * STUD_LDU * 0.04, 1),
                "height": round(courses * BRICK_LDU * 0.04, 1),
                "depth": round(relief_studs * STUD_LDU * 0.04, 1),
            },
            "cells": width * courses,
            # Cells the building actually occupies. The difference between this
            # and `cells` is the background that was segmented away.
            "buildingCells": int(cells_mask.sum()),
            "coverage": round(float(cells_mask.mean()), 3),
        },
        "structure": structure,
        # How much this looks like the photograph, whether it will stand up, and
        # whether it is a size anyone would build. The three are combined in
        # `overall`, which is what the search optimises.
        "fidelity": _fidelity(
            rgb, colours, depths, cells_mask, depth01, cells,
            structure=structure, pieces=total_pieces, piece_budget=piece_budget,
        ),
        "visiblePieceCount": sum(b["quantity"] for b in visible),
        "hiddenPieceCount": total_pieces - sum(b["quantity"] for b in visible),
        # numpy arrays and Cell tuples — feed them to the renderers, then drop the
        # key before the plan goes anywhere near JSON or the database.
        "_grids": {
            "depths": depths,
            "colours": colours,
            "cells": cells,
            "mask": cells_mask,
            "relief": relief_studs,
            # The photo on the stud grid. worst_regions compares against this, and
            # recomputing it from the original image would resample differently.
            "source": rgb,
        },
    }


# ---------------------------------------------------------------- renders


def _shade(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(int(max(0, min(255, c * factor))) for c in rgb)  # type: ignore[return-value]


def render_facade(
    depths: np.ndarray, colours: np.ndarray, scale: int = 16
) -> Image.Image:
    """The view the model is built for: square on, from the front.

    Cells are drawn 20:24 like the bricks they stand for, so this is the shape the
    finished wall has — not the shape of the sampling grid. Transparent where the
    building is not, so the silhouette is the building's.
    """
    from PIL import ImageDraw

    courses, width = depths.shape
    cw = scale
    ch = max(1, round(scale * BRICK_LDU / STUD_LDU))
    img = Image.new("RGBA", (width * cw, courses * ch), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(courses):
        for x in range(width):
            if depths[y, x] == 0:
                continue
            base = cat.COLOURS_BY_ID[int(colours[y, x])].rgb
            # Nearer bricks catch more light. This is the only cue a head-on view
            # has for depth, and without it the facade reads as flat paint.
            lit = 0.86 + 0.16 * (depths[y, x] - 1) / max(1, depths.max() - 1)
            px, py = x * cw, (courses - 1 - y) * ch  # row 0 is the ground course
            draw.rectangle([px, py, px + cw - 1, py + ch - 1], fill=(*_shade(base, lit), 255))
            # A stud, so it reads as brick rather than as a pixel.
            r = cw * 0.28
            mx, my = px + cw / 2, py + ch * 0.42
            draw.ellipse(
                [mx - r, my - r * 0.9, mx + r, my + r * 0.9],
                fill=(*_shade(base, lit * 1.10), 255),
                outline=(*_shade(base, lit * 0.78), 255),
            )
    return img


# Where the light comes from, in model coordinates: up, to the left, and in front.
# Any direction works; what matters is that it is off-axis, because a light on the
# camera axis produces no shading at all and the relief becomes invisible — which
# is exactly the failure the render loop exists to catch.
_LIGHT = np.array([-0.45, 0.55, 0.70])
_LIGHT = _LIGHT / np.linalg.norm(_LIGHT)


def render_model(
    depths: np.ndarray,
    colours: np.ndarray,
    scale: int = 12,
    tiled: np.ndarray | None = None,
) -> Image.Image:
    """What the built model would look like, lit — not what the grid contains.

    render_facade draws each cell with a brightness read straight off its depth,
    which makes depth *legible* but not *physical*: two models with different
    relief produce the same picture up to a contrast change. This one shades from
    the surface normal of the depth field and adds contact shadow, so a facade
    that steps forward casts onto the one behind it. That is what makes a scoring
    loop able to tell three studs of relief from five; before this it could not,
    and every sweep chose the shallower model because the extra depth cost pieces
    and bought nothing the score could see.

    Pass `tiled` to mark cells finished with a tile: they are drawn flat, because
    the absence of a stud is the whole visual point of putting one there.
    """
    courses, width = depths.shape
    solid = depths > 0
    if not solid.any():
        return Image.new("RGBA", (width * scale, courses * scale), (0, 0, 0, 0))

    # Heights in studs, with empty cells sunk to the back plane so the silhouette
    # edge shades like a real edge rather than like a cliff of unknown height.
    h = np.where(solid, depths.astype(np.float64), 0.0)

    # Surface normal of the height field. dx and dy are in LDU, not cells, or the
    # 20:24 cell aspect tilts every normal a consistent few degrees.
    dzdx = np.gradient(h, axis=1) * STUD_LDU / STUD_LDU
    dzdy = np.gradient(h, axis=0) * STUD_LDU / BRICK_LDU
    normal = np.stack([-dzdx, -dzdy, np.ones_like(h)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)

    lambert = np.clip(normal @ _LIGHT, 0.0, 1.0)

    # Contact shadow, cheaply: a cell is shadowed by whatever stands in front of it
    # toward the light. Stepping the height field along the light's screen
    # direction and keeping the running maximum is a one-pass approximation of
    # that, and enough for the scale involved.
    shadow = np.zeros_like(h)
    step_x, step_y = -1, 1  # the light's direction projected onto the facade
    occluder = h.copy()
    for k in range(1, 5):
        occluder = np.roll(np.roll(h, k * step_y, axis=0), k * step_x, axis=1) - k * 0.55
        shadow = np.maximum(shadow, occluder - h)
    lit = np.clip(0.30 + 0.70 * lambert - 0.22 * np.clip(shadow, 0, 2), 0.12, 1.25)

    rgb = np.array([cat.COLOURS_BY_ID[int(c)].rgb for c in colours.ravel()],
                   dtype=np.float64).reshape(courses, width, 3)
    shaded = np.clip(rgb * lit[..., None], 0, 255)

    cw = scale
    ch = max(1, round(scale * BRICK_LDU / STUD_LDU))
    # Row 0 is the ground course, so the array is flipped for display.
    pix = np.repeat(np.repeat(shaded[::-1], ch, axis=0), cw, axis=1)
    alpha = np.repeat(np.repeat(solid[::-1].astype(np.uint8) * 255, ch, axis=0), cw, axis=1)

    # Studs, as a shading stamp rather than a drawn ellipse: multiplying is faster
    # than a hundred thousand PIL calls and gives the same read at this size.
    yy, xx = np.mgrid[0:ch, 0:cw]
    r2 = ((xx - cw / 2) / (cw * 0.30)) ** 2 + ((yy - ch * 0.42) / (ch * 0.26)) ** 2
    stamp = np.where(r2 < 1.0, 1.0 + 0.16 * (1 - r2), 1.0)
    stamp = np.where((r2 >= 1.0) & (r2 < 1.35), 0.82, stamp)
    field = np.tile(stamp, (courses, width))
    if tiled is not None:
        flat = np.repeat(np.repeat(tiled[::-1], ch, axis=0), cw, axis=1)
        field = np.where(flat, 1.0, field)
    pix = np.clip(pix * field[..., None], 0, 255)

    out = np.dstack([pix.astype(np.uint8), alpha])
    return Image.fromarray(out, mode="RGBA")


def render_massing(
    depths: np.ndarray, colours: np.ndarray, scale: int = 12, skew: float = 0.5
) -> Image.Image:
    """A three-quarter view, to show that the thing has a depth at all.

    Oblique rather than perspective: parallel lines stay parallel, so the depth of
    each part of the facade can be read off directly instead of being guessed.
    """
    from PIL import ImageDraw

    courses, width = depths.shape
    relief = int(depths.max())
    cw = scale
    ch = max(1, round(scale * BRICK_LDU / STUD_LDU))
    dx = max(1, round(scale * skew))
    dy = max(1, round(scale * skew * 0.5))

    img = Image.new(
        "RGBA", (width * cw + relief * dx + 2, courses * ch + relief * dy + 2), (0, 0, 0, 0)
    )
    draw = ImageDraw.Draw(img)

    # Painter's algorithm: back layers first, then the ones in front of them.
    for z in range(relief):
        ox, oy = (relief - 1 - z) * dx, z * dy
        for y in range(courses):
            for x in range(width):
                if depths[y, x] <= z:
                    continue
                base = cat.COLOURS_BY_ID[int(colours[y, x])].rgb
                face = z == depths[y, x] - 1
                lit = 1.0 if face else 0.62
                px = x * cw + ox
                py = (courses - 1 - y) * ch + oy
                draw.rectangle(
                    [px, py, px + cw - 1, py + ch - 1],
                    fill=(*_shade(base, lit), 255),
                    outline=(*_shade(base, lit * 0.8), 255),
                )
    return img


def render_course_map(
    depths: np.ndarray, colours: np.ndarray, scale: int = 8, per_row: int = 4
) -> Image.Image:
    """One plan view per band of courses — what to lay down, seen from above."""
    from PIL import ImageDraw

    courses, width = depths.shape
    relief = int(depths.max())
    bands = list(range(0, courses, COURSES_PER_STEP))
    cols = min(per_row, len(bands))
    rows = -(-len(bands) // cols)
    pad = 10
    tile_w, tile_h = width * scale, relief * scale

    img = Image.new(
        "RGBA",
        (cols * (tile_w + pad) + pad, rows * (tile_h + pad + 14) + pad),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(img)
    for i, start in enumerate(bands):
        ox = pad + (i % cols) * (tile_w + pad)
        oy = pad + (i // cols) * (tile_h + pad + 14)
        draw.text((ox, oy), f"courses {start + 1}–{min(start + COURSES_PER_STEP, courses)}",
                  fill=(150, 150, 150, 255))
        top = oy + 14
        for x in range(width):
            d = int(depths[start:start + COURSES_PER_STEP, x].max(initial=0))
            for z in range(d):
                base = cat.COLOURS_BY_ID[int(colours[start, x])].rgb
                lit = 1.0 if z == d - 1 else 0.55
                px, py = ox + x * scale, top + (relief - 1 - z) * scale
                draw.rectangle([px, py, px + scale - 1, py + scale - 1],
                               fill=(*_shade(base, lit), 255))
    return img
