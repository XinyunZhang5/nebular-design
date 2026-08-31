"""Find the building's masses and make them read as architecture.

WHAT THIS FIXES

A reconstruction is a scanned surface, not a designed one. Measured on the Big
Ben mesh, the visible shell's cross-sections have a median run of one cell: the
wall of the tower wanders in and out by a stud as it climbs, because the mesh
does. A rectangle partitioner handed that produces exactly what it should — a
field of 1 x 1 bricks — and no catalogue of bigger parts can change it, because
there is no straight run for a bigger part to sit on. Adding Brick 24 x 12 to
the tables bought six per cent.

The fix is upstream of the partitioner. A building is not a smooth solid of
revolution, it is a stack of masses with flat walls, and the same mesh says so
plainly once you ask the right question: courses 15 to 40 of that tower all
have an 18 x 16 footprint. Twenty-five courses of one prism, wearing a one-cell
fringe of reconstruction noise.

So: segment the courses into bands of near-constant footprint, take one
canonical footprint per band by majority vote, clean the fringe off it, and give
every course in the band that same footprint. The wall becomes flat because the
building's wall *is* flat, and a flat wall has long runs for long bricks to
cover.

WHAT IT DELIBERATELY DOES NOT DO

An earlier attempt covered the solid with volume-maximal boxes. Twenty-five
boxes cover 76% of Big Ben, which sounds like the same idea and is not: a greedy
box grows across whatever gives it volume, so it eats half the tower and half
the base in one piece and the silhouette goes with it. Bands only ever merge
along the axis a building is actually uniform in, and never change a course's
vertical position. What a band cannot explain, it leaves alone — a tapering
spire stays a tapering spire, one course at a time.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

# Courses join a band while their footprint still looks like the band's. 0.82
# is loose enough to absorb the one-cell fringe that makes two courses of the
# same wall disagree, and tight enough that a real setback — a storey stepping
# in, a roof starting — ends the band instead of being averaged away.
BAND_IOU = 0.82

# Bands shorter than this are transitions, not masses: the taper of a spire, the
# lip of a cornice. Regularising them would flatten the very shape they carry,
# so they pass through untouched.
MIN_BAND_COURSES = 4

# A cell belongs to the band's canonical footprint if it is filled in at least
# this share of the band's courses. Half is the honest reading of "this wall is
# here": present in most of the band, not merely somewhere in it.
MAJORITY = 0.5

# Regularising must not eat the mass. If cleaning the fringe off a canonical
# footprint costs more than this share of it, the footprint was fringe all the
# way down — a lattice, a railing, an open frame — and the band is left alone.
MIN_KEPT = 0.70


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    union = np.count_nonzero(a | b)
    return 1.0 if union == 0 else np.count_nonzero(a & b) / union


def _dilate2(mask: np.ndarray) -> np.ndarray:
    """Grow a mask by one cell in the four lattice directions."""
    out = mask.copy()
    out[1:, :] |= mask[:-1, :]
    out[:-1, :] |= mask[1:, :]
    out[:, 1:] |= mask[:, :-1]
    out[:, :-1] |= mask[:, 1:]
    return out


def _open(mask: np.ndarray) -> np.ndarray:
    """Keep only cells that some fully-filled 2 x 2 block covers.

    Morphological opening under a 2 x 2 square, which is the smallest element
    that says what we mean: a stud of wall is real if it has a neighbour in both
    directions, and a one-cell fin sticking off a wall does not. The obvious
    4-connected version is wrong for this — opening a plain rectangle with a
    plus-shaped element does not give the rectangle back, it eats the corners —
    and a 3 x 3 square is too coarse, because it deletes any wall two studs
    thick, which is most of them.

    Out-of-grid counts as empty here and the result is still right at the edges:
    a wall flush against the bounding box keeps its outer row, because the block
    that covers it lies one row in. The building always touches the box — that
    is how the lattice is fitted — so this case is the common one, not the edge.
    """
    h, w = mask.shape
    if h < 2 or w < 2:
        return mask.copy()
    block = mask[:-1, :-1] & mask[1:, :-1] & mask[:-1, 1:] & mask[1:, 1:]
    out = np.zeros_like(mask)
    out[:-1, :-1] |= block
    out[1:, :-1] |= block
    out[:-1, 1:] |= block
    out[1:, 1:] |= block
    return out


def _close(mask: np.ndarray) -> np.ndarray:
    """Fill cells that no fully-empty 2 x 2 block covers. Opening's dual.

    Padded with empty space first. Without the pad, open space that runs off the
    edge of the grid has no room for a block to sit in, so the last row of it
    reads as a one-cell pocket and gets filled — a wall that stops one course
    short of the bounding box grows to meet it, and a model flush against the
    box gains a rind of invented material on every side.
    """
    padded = np.pad(mask, 1, constant_values=False)
    return ~_open(~padded)[1:-1, 1:-1]


def _denoise(footprint: np.ndarray) -> np.ndarray:
    """Square off a footprint: fill one-cell notches, shave one-cell spurs.

    Closing then opening, in that order. Closing first because a notch and a
    spur next to each other are the same wobble seen from two sides, and filling
    the notch turns the pair into a straight edge that the opening then has
    nothing to do to.
    """
    return _open(_close(footprint))


def _majority(courses: np.ndarray) -> np.ndarray:
    return courses.mean(axis=0) >= MAJORITY


def bands(filled: np.ndarray, iou_floor: float = BAND_IOU) -> list[tuple[int, int]]:
    """Split the courses into runs that share a footprint. Half-open [y0, y1).

    Compared on denoised footprints, not raw ones. Two courses of one flat wall
    disagree by their own fringe — three stray cells each is enough to put the
    overlap under any useful threshold — so band-finding on raw courses splits
    a twenty-five course prism into twenty-five bands and regularises none of
    them. Denoising first asks the question that was meant: is this the same
    wall, ignoring the wobble that is the whole reason we are here.
    """
    clean = np.stack([_denoise(layer) for layer in filled])
    out: list[tuple[int, int]] = []
    start = 0
    for y in range(1, len(clean)):
        if _iou(clean[y], _majority(clean[start:y])) < iou_floor:
            out.append((start, y))
            start = y
    out.append((start, len(clean)))
    return out, clean


def regularise(
    filled: np.ndarray,
    iou_floor: float = BAND_IOU,
    min_courses: int = MIN_BAND_COURSES,
) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Give every course in a mass the same clean footprint.

    Returns the new solid and the bands that were actually regularised — the
    caller wants those, because a band is one prism and a prism is one thing to
    build, which is a far better assembly step than "course 23".
    """
    out = filled.copy()
    applied: list[tuple[int, int]] = []
    spans, clean_courses = bands(filled, iou_floor)

    for y0, y1 in spans:
        if y1 - y0 < min_courses:
            continue
        canonical = _majority(filled[y0:y1])
        if not canonical.any():
            continue
        clean = _denoise(_majority(clean_courses[y0:y1]))
        if clean.sum() < MIN_KEPT * canonical.sum():
            # Mostly fringe: a frame or a railing, where the one-cell detail is
            # the structure rather than noise on it.
            continue
        if not clean.any():
            continue
        out[y0:y1] = clean
        applied.append((y0, y1))

    if applied:
        logger.info(
            "massing: %d band(s) regularised, %s; %d cells -> %d",
            len(applied),
            ", ".join(f"c{a}-{b - 1}" for a, b in applied),
            int(filled.sum()),
            int(out.sum()),
        )
    return out, applied


# Six-neighbourhood, as (axis, step) pairs.
_DIRS = ((0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1))


def _shifted(a: np.ndarray, axis: int, step: int) -> np.ndarray:
    """Shift along one lattice axis, filling the vacated face with zeros.

    np.roll would wrap, which quietly teleports the colour of the spire onto the
    ground course.
    """
    out = np.zeros_like(a)
    dst: list[slice] = [slice(None)] * a.ndim
    src: list[slice] = [slice(None)] * a.ndim
    if step > 0:
        dst[axis], src[axis] = slice(step, None), slice(None, -step)
    else:
        dst[axis], src[axis] = slice(None, step), slice(-step, None)
    out[tuple(dst)] = a[tuple(src)]
    return out


def inpaint_colours(
    rgb: np.ndarray, known: np.ndarray, filled: np.ndarray, rounds: int = 16
) -> np.ndarray:
    """Give the cells regularising created a colour, grown in from their neighbours.

    Squaring off a footprint fills notches, and a cell that was not in the mesh
    was never sampled from the photo. Left alone it is (0, 0, 0), which survives
    quantisation as a real colour and paints black scars down the side of every
    wall this module straightened.
    """
    out = rgb.astype(np.float32).copy()
    have = known.copy()
    for _ in range(rounds):
        need = filled & ~have
        if not need.any():
            break
        acc = np.zeros_like(out)
        cnt = np.zeros(filled.shape, dtype=np.float32)
        for axis, step in _DIRS:
            acc += _shifted(out * have[..., None], axis, step)
            cnt += _shifted(have.astype(np.float32), axis, step)
        grow = need & (cnt > 0)
        if not grow.any():
            break
        out[grow] = acc[grow] / cnt[grow][:, None]
        have |= grow
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- colour

# Smoothing passes over the quantised palette. Two is enough to turn a speckled
# wall into fields; more starts dissolving details that are genuinely one stud
# wide, like the gold band under a cornice.
COLOUR_ROUNDS = 2

# Faces, as the (axis, step) of the neighbour whose absence exposes them. Only
# the five that can be seen: nothing looks at the underside of a model.
_FACES = ((2, 1), (2, -1), (1, 1), (1, -1), (0, 1))


def _box3(a: np.ndarray) -> np.ndarray:
    """Sum over a 3 x 3 x 3 neighbourhood, separably."""
    out = a
    for axis in (0, 1, 2):
        out = out + _shifted(out, axis, 1) + _shifted(out, axis, -1)
    return out


def flatten_colours(
    colours: np.ndarray,
    filled: np.ndarray,
    visible: np.ndarray,
    rounds: int = COLOUR_ROUNDS,
) -> np.ndarray:
    """Group the surface into colour fields, one face at a time.

    WHY THIS IS THE BINDING CONSTRAINT

    Straightening the walls takes the visible shell's geometric runs from a
    median of one cell to a median of two — and buys almost nothing, because the
    partitioner is not cutting on geometry any more. Measured on the same model
    after regularising: the geometric runs average 2.97 cells, and the runs of
    *constant colour* average 1.40, with 78% of them a single cell. A brick may
    not straddle two colours, so the colour field is what decides how big a
    brick can be, and a reconstruction's vertex colours are per-cell noise.

    WHY IT IS DONE PER FACE

    The obvious fix — a mode filter over the volume — was tried and made the
    model worse: it smooths across corners, so the colour of the south wall
    bleeds around the edge onto the west wall, and a dark roof pulls a grey halo
    down the storey below it. Each cell here is smoothed only against cells that
    face the same way, which is the same rule a wall obeys in real life. The
    filter is a 3 x 3 x 3 mode restricted to that face; a cell keeps its own
    colour on a tie, so a field only moves when its neighbourhood outvotes it.
    """
    ids = np.unique(colours[filled])
    if len(ids) < 2:
        return colours

    faces = [filled & visible & ~_shifted(filled, axis, step) for axis, step in _FACES]
    out = colours.copy()

    for _ in range(rounds):
        for face in faces:
            if not face.any():
                continue
            # Only cells on this face vote, and only for cells on this face.
            face_counts = np.stack(
                [_box3(((out == cid) & face).astype(np.int32)) for cid in ids]
            )
            winner = ids[face_counts.argmax(axis=0)]
            own = np.take_along_axis(
                face_counts,
                np.searchsorted(ids, out)[None],
                axis=0,
            )[0]
            keep = own >= face_counts.max(axis=0)
            out = np.where(face & ~keep, winner, out)
    return out


# Luminance weights, Rec. 709.
_LUMA = np.array([0.2126, 0.7152, 0.0722])

# How far a face's exposure may be pushed. A facade in full sun against one in
# shadow measures a ratio of about 1.5 on a clear photograph; the cap is above
# that and well below the point where correcting an almost-black face amplifies
# its noise into confetti.
MAX_GAIN = 2.2


def neutralise_shading(
    rgb: np.ndarray, filled: np.ndarray, visible: np.ndarray
) -> np.ndarray:
    """Take the photograph's lighting back out of the colours.

    THE PROBLEM THIS SOLVES

    A photograph records a material times its illumination, and the pipeline
    quantises the product. Measured on Big Ben: the sunlit west face averages RGB
    (122, 98, 75), the shaded east face (75, 65, 58) — one limestone wall,
    photographed at a ratio of 1.5, arriving at the palette as two different
    LEGO colours. It is why the tower came out mottled brown and grey instead of
    honey, and why Black took 22% of the piece count on a building that has none.

    A real set does not work that way. The Ministry of Magic's walls are one
    colour of brick and the shading is done by the light in the room. So: measure
    each face's mean luminance, scale each face toward the model's overall mean,
    and let the renderer put the shadow back — which `render_isometric` already
    does, by darkening faces according to which way they point.

    Only the exposure is corrected, not the hue: the gain is a single scalar per
    face, so a genuinely green roof stays green and only stops being a darker
    green than the wall it sits on for reasons of weather.
    """
    lit = filled & visible
    if not lit.any():
        return rgb

    values = rgb.astype(np.float32)
    target = float((values[lit] @ _LUMA).mean())
    if target <= 1.0:
        return rgb

    gain_sum = np.zeros(filled.shape, dtype=np.float32)
    gain_n = np.zeros(filled.shape, dtype=np.float32)
    for axis, step in _FACES:
        face = lit & ~_shifted(filled, axis, step)
        if not face.any():
            continue
        mean = float((values[face] @ _LUMA).mean())
        if mean <= 1.0:
            continue
        gain = float(np.clip(target / mean, 1.0 / MAX_GAIN, MAX_GAIN))
        gain_sum[face] += gain
        gain_n[face] += 1.0

    # A cell on two faces — the corner of a building — gets the average of both,
    # so an edge does not step in brightness between its two walls.
    scale = np.ones(filled.shape, dtype=np.float32)
    both = gain_n > 0
    scale[both] = gain_sum[both] / gain_n[both]
    return np.clip(values * scale[..., None], 0, 255).astype(np.uint8)
