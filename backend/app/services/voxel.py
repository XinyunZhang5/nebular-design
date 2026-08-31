"""Turn a reconstructed mesh into a solid on the LEGO lattice.

This is the step that replaces the depth-map relief. `legolize` builds from a
`depths[course, stud]` heightfield: one number per column saying how far the
facade is pushed forward, which by construction can only ever describe a wall
seen from the front. A photograph plus a depth map cannot say more than that,
because a single view carries no information about the back of the subject.

A reconstructed mesh does carry it. What arrives here is a closed surface in
TripoSR's frame; what leaves is an occupancy grid on the brick lattice, so the
model has a back, a left side and a right side that were reconstructed rather
than extruded.

THE LATTICE IS NOT CUBIC

A stud is 20 LDU across and a course is 24 LDU tall, so the voxel is 20x24x20
and the vertical axis has to be sampled 20% more coarsely than the other two.
Sampling on a cube and building in courses stretches the model vertically by a
fifth — the same trap the relief path documents, in three dimensions.

AXES

TripoSR's frame is documented in `get_spherical_cameras`: x back, y right,
z up. The lattice arrays are indexed [course, depth, stud] to match the order
`legolize` already uses, so the permutation is:

    mesh y (right)  ->  stud   x, across the facade
    mesh x (back)   ->  depth  z, 0 at the back plane
    mesh z (up)     ->  course y, 0 at the ground course

WHY THE SOLID IS FILLED AND THEN PRUNED

Marching cubes returns a shell. A shell is not buildable: its courses are rings
that would need each layer to grip the one below at exactly the ring's
footprint, which nothing guarantees. Filling the interior makes every brick rest
on brick. Pruning afterwards drops the pieces the reconstruction left floating
in mid-air, which a photograph's background haze reliably produces a few of.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

import numpy as np

logger = logging.getLogger(__name__)

STUD_LDU = 20  # a stud, across the facade and into it
BRICK_LDU = 24  # a course, upward

# A course is 1.2 studs tall. Everything vertical is sampled through this.
COURSE_PER_STUD = BRICK_LDU / STUD_LDU

# Below this share of the total filled volume, a disconnected lump is
# reconstruction noise rather than part of the building — a scrap of sky that
# survived segmentation, or a tree the mesh grew into a blob.
MIN_COMPONENT_SHARE = 0.02


class Solid(NamedTuple):
    """An occupancy grid on the brick lattice, indexed [course, depth, stud]."""

    filled: np.ndarray  # bool
    rgb: np.ndarray  # uint8, (..., 3); meaningful only where `visible`
    visible: np.ndarray  # bool: has at least one empty face, so it can be seen

    @property
    def shape_studs(self) -> tuple[int, int, int]:
        """(courses, depth in studs, width in studs)."""
        return self.filled.shape  # type: ignore[return-value]

    @property
    def count(self) -> int:
        return int(self.filled.sum())


def _to_lattice_indices(vertices: np.ndarray, max_studs: int) -> tuple[np.ndarray, float]:
    """Map mesh vertices into lattice index space, one unit per voxel.

    Scaled so the model is `max_studs` wide, which is the dimension a builder
    reads first and the one the piece budget is set against.
    """
    # mesh (x=depth, y=across, z=up) -> lattice (across, depth, up)
    across, depth, up = vertices[:, 1], vertices[:, 0], vertices[:, 2]

    lo = np.array([across.min(), depth.min(), up.min()])
    span = np.array([np.ptp(across), np.ptp(depth), np.ptp(up)])
    if span[0] <= 0:
        raise ValueError("mesh has no width; nothing to build")

    # One stud of world size. The vertical axis then divides by 1.2 of it,
    # because a course is 1.2 studs tall.
    stud_world = span[0] / max_studs
    cell = np.array([stud_world, stud_world, stud_world * COURSE_PER_STUD])

    idx = (np.stack([across, depth, up], axis=1) - lo) / cell
    return idx, stud_world


def _surface_voxels(idx: np.ndarray, faces: np.ndarray, dims: np.ndarray) -> np.ndarray:
    """Rasterise every triangle into the grid.

    Subdivides each triangle until no edge is longer than half a voxel, then
    rounds the points. Sampling only the vertices leaves holes wherever a
    triangle is larger than a voxel, and marching cubes at 256 against a
    lattice of 48 produces those constantly.
    """
    v = idx[faces]  # (F, 3, 3)
    pts = [v.reshape(-1, 3)]

    # Subdividing every triangle uniformly is wasteful when most are already
    # small, but the check is cheap and the loop runs a handful of times.
    for _ in range(8):
        edges = np.stack(
            [v[:, 1] - v[:, 0], v[:, 2] - v[:, 1], v[:, 0] - v[:, 2]], axis=1
        )
        longest = np.linalg.norm(edges, axis=2).max(axis=1)
        big = longest > 0.5
        if not big.any():
            break
        b = v[big]
        mid = np.stack(
            [(b[:, 0] + b[:, 1]) / 2, (b[:, 1] + b[:, 2]) / 2, (b[:, 2] + b[:, 0]) / 2],
            axis=1,
        )
        v = np.concatenate(
            [
                np.stack([b[:, 0], mid[:, 0], mid[:, 2]], axis=1),
                np.stack([mid[:, 0], b[:, 1], mid[:, 1]], axis=1),
                np.stack([mid[:, 2], mid[:, 1], b[:, 2]], axis=1),
                mid,
            ]
        )
        pts.append(v.reshape(-1, 3))

    p = np.rint(np.concatenate(pts)).astype(np.int64)
    np.clip(p, 0, dims - 1, out=p)
    grid = np.zeros(tuple(dims), dtype=bool)
    grid[p[:, 0], p[:, 1], p[:, 2]] = True
    return grid


def _fill_interior(shell: np.ndarray) -> np.ndarray:
    """Everything the shell encloses.

    Flood from outside a one-cell margin rather than calling
    `binary_fill_holes`: a reconstruction is not reliably watertight — a mesh
    that runs off the edge of the marching-cubes grid is open along that face —
    and hole filling on an open shell fills nothing at all, leaving a hollow
    model that cannot stand. Flooding treats every cell the outside cannot
    reach as interior, which is the answer that degrades gracefully.
    """
    from scipy import ndimage

    padded = np.pad(shell, 1, constant_values=False)
    outside = np.zeros_like(padded)
    outside[0, 0, 0] = True
    outside = ndimage.binary_propagation(outside, mask=~padded)
    return (~outside)[1:-1, 1:-1, 1:-1]


def _largest_body(filled: np.ndarray) -> np.ndarray:
    """Drop lumps that float free of the building."""
    from scipy import ndimage

    labels, n = ndimage.label(filled)
    if n <= 1:
        return filled
    sizes = ndimage.sum_labels(filled, labels, index=np.arange(1, n + 1))
    total = sizes.sum()
    keep = np.flatnonzero(sizes >= max(sizes.max() * MIN_COMPONENT_SHARE, 1)) + 1
    dropped = n - len(keep)
    if dropped:
        logger.info(
            "voxel: dropped %d floating lump(s), %d of %d cells",
            dropped, int(total - sizes[keep - 1].sum()), int(total),
        )
    return np.isin(labels, keep)


def _stand_flat(filled: np.ndarray) -> np.ndarray:
    """Cut the model off at its widest low course and stand it on that.

    Reconstruction returns an object floating in space, and the bottom of one is
    rounded: the lowest courses of a tower come back as a stub a few studs
    across that the real base then flares out from. Built literally that is a
    building balanced on a point — three courses of Big Ben's plinth had nothing
    beneath them, and the partitioner threw away everything it could not anchor.

    A building meets the ground on its footprint, so the widest course in the
    bottom eighth is the ground, and anything below it is reconstruction dross.
    """
    footprint = filled.reshape(len(filled), -1).sum(axis=1)
    low = max(1, len(filled) // 8)
    base = int(np.argmax(footprint[: low + 1]))
    if base == 0:
        return filled
    logger.info(
        "voxel: trimmed %d course(s) of rounded base (%d -> %d cells across)",
        base, int(footprint[0]), int(footprint[base]),
    )
    return filled[base:]


def _largest_box(remaining: np.ndarray) -> tuple[int, tuple[int, int, int, int, int, int]] | None:
    """The biggest axis-aligned box of set cells, by volume.

    Maximal-rectangle-under-a-histogram per course, then grown upward while the
    courses above still hold the same footprint. The histogram scan is the
    classic stack method and is linear in the layer; the growth is a slice test.
    """
    courses, depth, width = remaining.shape
    best: tuple[int, tuple[int, int, int, int, int, int]] | None = None

    for y0 in range(courses):
        layer = remaining[y0]
        if not layer.any():
            continue
        heights = np.zeros(width, dtype=np.int32)
        for z in range(depth):
            heights = np.where(layer[z], heights + 1, 0)
            stack: list[tuple[int, int]] = []
            for x in range(width + 1):
                here = int(heights[x]) if x < width else 0
                start = x
                while stack and stack[-1][1] >= here:
                    start, tall = stack.pop()
                    area = tall * (x - start)
                    if not area:
                        continue
                    z0, z1 = z - tall + 1, z + 1
                    y1 = y0 + 1
                    while y1 < courses and remaining[y1, z0:z1, start:x].all():
                        y1 += 1
                    volume = area * (y1 - y0)
                    if best is None or volume > best[0]:
                        best = (volume, (y0, y1, z0, z1, start, x))
                stack.append((start, here))
    return best


def boxify(
    filled: np.ndarray, coverage: float = 0.90, min_volume: int = 6, cap: int = 96
) -> np.ndarray:
    """Approximate the solid by a handful of boxes, and build those instead.

    This is the difference between a model that reads as a scan and one that
    reads as a building. A reconstruction's surface is bumpy, so every course's
    cross-section is a wobbling ring one or two cells thick, and a rectangle
    partitioner covering a wobbling ring has nothing to reach for but 1x1 and
    1x2 bricks — measured at 36% of the parts list, and no amount of colour
    reduction or surface smoothing moved it, because the cause is the shape.

    Boxes are what the building actually is. Greedily decomposed, 25 of them
    cover 76% of Big Ben and 50 cover 86%; the largest is the tower shaft, 19
    courses by 15 by 12, in one piece. Rebuilding the solid as their union makes
    every wall planar and every course's cross-section a rectangle, which is the
    shape long bricks exist for — and it is also what a set designer does when
    they look at a photograph and start with a box.

    What is thrown away is the tail: the boxes past `coverage` are single cells
    of reconstruction noise, and they are the ones that were costing the most
    parts.
    """
    total = int(filled.sum())
    if not total:
        return filled
    remaining = filled.copy()
    out = np.zeros_like(filled)
    covered = 0
    boxes = 0
    for _ in range(cap):
        best = _largest_box(remaining)
        if best is None or best[0] < min_volume:
            break
        volume, (y0, y1, z0, z1, x0, x1) = best
        remaining[y0:y1, z0:z1, x0:x1] = False
        out[y0:y1, z0:z1, x0:x1] = True
        covered += volume
        boxes += 1
        if covered / total >= coverage:
            break
    logger.info(
        "voxel: %d box(es) cover %.0f%% of %d cells",
        boxes, 100 * covered / total, total,
    )
    return out


def _visible(filled: np.ndarray) -> np.ndarray:
    """Cells with at least one face open to the air.

    Everything else is buried and gets the fill colour, because a colour nobody
    can see is a colour the parts list should not be spending on.
    """
    padded = np.pad(filled, 1, constant_values=False)
    exposed = np.zeros_like(filled)
    for axis in range(3):
        for shift in (-1, 1):
            sl = [slice(1, -1)] * 3
            sl[axis] = slice(1 + shift, (-1 + shift) or None)
            exposed |= ~padded[tuple(sl)]
    return exposed & filled


def _colours(
    idx: np.ndarray, vertex_rgb: np.ndarray, visible: np.ndarray
) -> np.ndarray:
    """Give every visible cell the colour of the nearest surface point."""
    from scipy.spatial import cKDTree

    rgb = np.zeros(visible.shape + (3,), dtype=np.uint8)
    where = np.argwhere(visible)
    if not len(where):
        return rgb
    centres = where + 0.5
    _, nearest = cKDTree(idx).query(centres, k=1, workers=-1)
    rgb[visible] = vertex_rgb[nearest]
    return rgb


def voxelise(mesh, max_studs: int = 48, box_coverage: float = 0.0) -> Solid:
    """Mesh -> occupancy grid on the brick lattice.

    `max_studs` is the width of the finished model. It is the piece-count dial:
    the solid grows roughly with its cube, so 64 is about twice the parts of 48.

    `box_coverage` above zero replaces the solid with the boxes that cover that
    fraction of it — see `boxify`. It is off by default because of what it costs:
    measured on Big Ben at 0.85 it takes the parts list from 2055 to 1595, and
    takes the tower's silhouette with it. Worth having as a dial for anyone who
    wants the cheaper build; not worth having as the default.
    """
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    if not len(faces):
        raise ValueError("mesh has no faces; nothing to build")

    idx, stud_world = _to_lattice_indices(vertices, max_studs)
    dims = np.maximum(np.ceil(idx.max(axis=0)).astype(int) + 1, 1)

    shell = _surface_voxels(idx, faces, dims)
    filled = _largest_body(_fill_interior(shell))
    if box_coverage > 0:
        filled = _largest_body(boxify(filled, coverage=box_coverage))

    # Lattice order is (across, depth, up); the arrays are [course, depth, stud].
    filled = np.transpose(filled, (2, 1, 0))
    idx_arr = idx[:, [2, 1, 0]]
    before = len(filled)
    filled = _stand_flat(filled)
    idx_arr[:, 0] -= before - len(filled)

    visible = _visible(filled)
    vertex_rgb = _vertex_rgb(mesh, len(vertices))
    rgb = _colours(idx_arr, vertex_rgb, visible)

    logger.info(
        "voxel: %d x %d studs x %d courses, %d cells (%d visible), stud = %.4f world",
        filled.shape[2], filled.shape[1], filled.shape[0],
        filled.sum(), visible.sum(), stud_world,
    )
    return Solid(filled=filled, rgb=rgb, visible=visible)


def _vertex_rgb(mesh, n: int) -> np.ndarray:
    """Vertex colours as RGB, or mid-grey if the mesh carries none."""
    colours = getattr(mesh.visual, "vertex_colors", None)
    if colours is None or len(colours) != n:
        return np.full((n, 3), 128, dtype=np.uint8)
    return np.asarray(colours)[:, :3].astype(np.uint8)
