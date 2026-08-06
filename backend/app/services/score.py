"""Score a build plan against the photograph it came from.

The pipeline could not tell a good result from a bad one. It produced a model,
checked that the parts added up, and shipped it — so a night photograph of a
building behind bare trees came out as a navy-and-brown lump with a lamp post
floating beside it, and every internal check passed, because the lump was
internally consistent. `_check` verifies the plan is *coherent*. Nothing verified
it was *like the photo*.

This module supplies the missing number. It is the piece every published approach
in this area has and this one did not: Legolization (SIGGRAPH Asia 2015) refines
the layout around whatever its stability analysis scores worst, and BrickGPT
(ICCV 2025) rolls generation back whenever its validity check fails. Both are
closed loops around a metric. Without one there is nothing to iterate on and no
way to choose between two settings except by looking.

Three measurements, because a single one is gameable:

    silhouette   Is it the right shape? IoU of the built cells against the
                 segmented building. Insensitive to colour, so it keeps scoring
                 when the photo is too dark to have any.
    colour       Is it the right colour? Mean CIEDE2000 between each cell's source
                 colour and the LEGO colour chosen for it. CIEDE2000 rather than
                 RGB distance because the question is whether a person would call
                 it the same colour, and RGB distance answers a different one.
    detail       Does it have the right features? Correlation of the two
                 luminance gradient fields. This is what falls when a wall is
                 smoothed until the windows vanish, and neither of the other two
                 notices that.

They deliberately disagree. A model can be the right shape and the wrong colour,
or the right colour and mush. Reporting one number and hiding the others would
throw away the part that says *what* to fix.
"""

from __future__ import annotations

import numpy as np

# sRGB -> XYZ, D65. The standard matrix; see IEC 61966-2-1.
_RGB_TO_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
_WHITE_D65 = np.array([0.95047, 1.00000, 1.08883])


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Convert 0-255 sRGB to CIE L*a*b*. Accepts any shape ending in 3."""
    srgb = np.asarray(rgb, dtype=np.float64) / 255.0
    # Undo the sRGB transfer function. Skipping this — treating the stored byte as
    # linear light — is the usual mistake, and it makes every dark colour compare
    # as far closer to black than the eye finds it.
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    xyz = linear @ _RGB_TO_XYZ.T / _WHITE_D65

    eps = 216 / 24389
    kappa = 24389 / 27
    f = np.where(xyz > eps, np.cbrt(xyz), (kappa * xyz + 16) / 116)
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    return np.stack([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)], axis=-1)


def delta_e_2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """CIEDE2000 colour difference, elementwise over matching-shaped Lab arrays.

    The full formula, including the hue-rotation term. Around 1.0 is the just-
    noticeable difference; 2-3 is a colour a person would call the same; past 10
    they are plainly different colours.
    """
    l1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    l2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]

    c1, c2 = np.hypot(a1, b1), np.hypot(a2, b2)
    c_bar = (c1 + c2) / 2
    g = 0.5 * (1 - np.sqrt(c_bar**7 / (c_bar**7 + 25.0**7 + 1e-12)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360

    dlp = l2 - l1
    dcp = c2p - c1p
    dhp = h2p - h1p
    dhp = np.where(dhp > 180, dhp - 360, np.where(dhp < -180, dhp + 360, dhp))
    dhp = np.where(c1p * c2p == 0, 0.0, dhp)
    dHp = 2 * np.sqrt(c1p * c2p) * np.sin(np.radians(dhp) / 2)

    lp_bar = (l1 + l2) / 2
    cp_bar = (c1p + c2p) / 2
    hsum = h1p + h2p
    hdiff = np.abs(h1p - h2p)
    hp_bar = np.where(
        c1p * c2p == 0, hsum,
        np.where(hdiff <= 180, hsum / 2,
                 np.where(hsum < 360, (hsum + 360) / 2, (hsum - 360) / 2)),
    )

    t = (1 - 0.17 * np.cos(np.radians(hp_bar - 30))
         + 0.24 * np.cos(np.radians(2 * hp_bar))
         + 0.32 * np.cos(np.radians(3 * hp_bar + 6))
         - 0.20 * np.cos(np.radians(4 * hp_bar - 63)))
    d_theta = 30 * np.exp(-(((hp_bar - 275) / 25) ** 2))
    rc = 2 * np.sqrt(cp_bar**7 / (cp_bar**7 + 25.0**7 + 1e-12))
    sl = 1 + (0.015 * (lp_bar - 50) ** 2) / np.sqrt(20 + (lp_bar - 50) ** 2)
    sc = 1 + 0.045 * cp_bar
    sh = 1 + 0.015 * cp_bar * t
    rt = -np.sin(np.radians(2 * d_theta)) * rc

    return np.sqrt(
        (dlp / sl) ** 2 + (dcp / sc) ** 2 + (dHp / sh) ** 2
        + rt * (dcp / sc) * (dHp / sh)
    )


def _local_mean(rgb: np.ndarray, mask: np.ndarray, r: int = 1) -> np.ndarray:
    """Average each cell with its neighbours, ignoring anything outside the mask.

    How the model looks from a step back. Masked so the background — which is not
    built and whose colour means nothing — cannot bleed across the silhouette and
    make the outermost studs score against a blend of building and sky.
    """
    w = mask.astype(np.float64)
    acc = np.zeros_like(rgb, dtype=np.float64)
    cnt = np.zeros(mask.shape, dtype=np.float64)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            acc += np.roll(np.roll(rgb * w[..., None], dy, axis=0), dx, axis=1)
            cnt += np.roll(np.roll(w, dy, axis=0), dx, axis=1)
    return acc / np.maximum(cnt, 1)[..., None]


def _luminance(rgb: np.ndarray) -> np.ndarray:
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def _gradients(a: np.ndarray) -> np.ndarray:
    """Sobel magnitude, without a scipy dependency."""
    p = np.pad(a.astype(np.float64), 1, mode="edge")
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])
    return np.hypot(gx, gy)


def score(
    source_rgb: np.ndarray,
    built_rgb: np.ndarray,
    source_mask: np.ndarray,
    built_mask: np.ndarray,
    source_depth: np.ndarray | None = None,
    built_depth: np.ndarray | None = None,
    lit_rgb: np.ndarray | None = None,
    structure: dict | None = None,
    pieces: int | None = None,
    piece_budget: int = 1500,
) -> dict[str, float]:
    """How much the built model looks like the photo. All four grids share a shape.

    `source_rgb` is the photo sampled onto the stud grid; `built_rgb` is the LEGO
    colour actually placed in each cell. `source_mask` is the segmented building;
    `built_mask` is where bricks ended up — the two differ wherever the pipeline
    dropped something, which is exactly what the silhouette term measures.
    """
    inter = float((source_mask & built_mask).sum())
    union = float((source_mask | built_mask).sum())
    silhouette = inter / union if union else 0.0

    # Colour, at two scales, and the second one exists because the first is unfair
    # to dithering.
    #
    # Error diffusion deliberately makes individual cells the wrong colour so that
    # the local average comes out right — that is the entire mechanism. Scored per
    # cell it therefore has to lose, and it did: turning dithering on raised the
    # per-cell figure on every photograph tried, while the render plainly looked
    # closer. A metric that cannot express the benefit of a technique will always
    # reject it, and the fault is the metric's.
    #
    # The eye does both. Studs on a built model are large enough to resolve
    # individually and close enough together to blend at a few paces, so neither
    # number alone is the perceived colour and the score uses their mean.
    both = source_mask & built_mask
    if both.any():
        lab_s, lab_b = srgb_to_lab(source_rgb), srgb_to_lab(built_rgb)
        per_cell = float(delta_e_2000(lab_s[both], lab_b[both]).mean())
        blur_s, blur_b = _local_mean(source_rgb, both), _local_mean(built_rgb, both)
        local = float(delta_e_2000(srgb_to_lab(blur_s)[both], srgb_to_lab(blur_b)[both]).mean())
        colour_de = (per_cell + local) / 2
    else:
        per_cell = local = colour_de = 100.0

    # Detail is measured on the *lit* render when one is supplied. Comparing flat
    # cell colours to a photograph asks whether the palette matches; comparing a
    # lit render to it asks whether the built object looks like the photographed
    # one, which is the actual question and the only version that can see relief,
    # slopes or a tiled edge at all.
    render = lit_rgb if lit_rgb is not None else built_rgb
    gs, gb = _gradients(_luminance(source_rgb)), _gradients(_luminance(render))
    if both.any() and gs[both].std() > 1e-6 and gb[both].std() > 1e-6:
        detail = float(np.corrcoef(gs[both], gb[both])[0, 1])
    else:
        detail = 0.0

    # Relief: does the built depth follow the depth the photo implies?
    #
    # This is the term that was missing, and its absence had a specific
    # consequence — three studs of relief and five scored identically, so every
    # sweep picked three, because the extra depth cost pieces and bought nothing
    # measurable. Correlation rather than error, because the depth map is relative:
    # a monocular estimate says what is nearer, not how much nearer in centimetres.
    relief = 0.0
    if source_depth is not None and built_depth is not None and both.any():
        sd, bd = source_depth[both], built_depth[both].astype(np.float64)
        if sd.std() > 1e-6 and bd.std() > 1e-6:
            relief = float(np.corrcoef(sd, bd)[0, 1])

    # Weights, with the reasoning rather than a claim of optimality. Shape carries
    # most of whether a model reads as the building at all. Colour is mapped to a
    # palette of a dozen, so even a good result cannot score near zero — 12 is
    # treated as the floor of usable and the term scaled to it. Detail and relief
    # split what is left: they are what separate a model from a photograph glued
    # to a wall.
    fidelity = (
        0.40 * silhouette
        + 0.25 * max(0.0, 1.0 - colour_de / 12.0)
        + 0.20 * max(0.0, detail)
        + 0.15 * max(0.0, relief)
    )

    # Buildability and size are multipliers, not further terms in the sum, and the
    # difference matters. As another weighted term, a model with thirty spans
    # hanging in mid-air scores a few percent below one that stands up, and the
    # search happily picks it for a slightly better colour match. As a multiplier
    # it cannot: a model that will not hold itself together is not a slightly
    # worse model of the building, and one you cannot afford the parts for is not
    # a model at all.
    #
    # Both are gentle rather than cliff-edged, because both are matters of degree —
    # a couple of short unsupported runs is a note in the instructions, not a
    # failure, and being ten percent over budget is not the same as being triple.
    # The two kinds of unsupported span are not the same problem, and lumping
    # them cost the search a resolution tier. A lintel is anchored at both ends —
    # every window in every LEGO building has one, and past about eight studs it
    # wants a plate across the joint. A floating run is anchored at neither: it is
    # brick over air, and no note in the instructions fixes it.
    spans = 0 if structure is None else int(structure.get("spansNeedingSupport", 0))
    floating = 0 if structure is None else int(structure.get("floatingRuns", 0))
    long_lintels = max(0, spans - floating)
    buildable = 1.0 / (1.0 + floating / 10.0 + long_lintels / 40.0)
    size_fit = 1.0 if not pieces else min(1.0, (piece_budget / pieces) ** 0.5)

    overall = fidelity * buildable * size_fit
    return {
        "fidelity": round(fidelity, 4),
        "buildable": round(buildable, 4),
        "sizeFit": round(size_fit, 4),
        "spansNeedingSupport": spans,
        "silhouette": round(silhouette, 4),
        "colourDeltaE": round(colour_de, 2),
        # Both halves, because they say different things: a large gap between
        # them means the model is locally right and individually noisy, which is
        # what dithering trades for and what a viewer may or may not want.
        "colourDeltaEPerCell": round(per_cell, 2),
        "colourDeltaELocal": round(local, 2),
        "detail": round(detail, 4),
        "relief": round(relief, 4),
        "overall": round(overall, 4),
    }


def worst_regions(
    source_rgb: np.ndarray,
    built_rgb: np.ndarray,
    both: np.ndarray,
    tiles: int = 6,
) -> list[dict[str, float]]:
    """Where the model departs most from the photo, as a coarse grid of tiles.

    The point of a score is to say what to fix next, and a single number cannot.
    This splits the facade into tiles and ranks them by colour error, so a caller
    can spend more resolution — or more brick types — where it will show.
    """
    h, w = both.shape
    out: list[dict[str, float]] = []
    ys = np.linspace(0, h, tiles + 1).astype(int)
    xs = np.linspace(0, w, tiles + 1).astype(int)
    for i in range(tiles):
        for j in range(tiles):
            sel = np.zeros_like(both)
            sel[ys[i]:ys[i + 1], xs[j]:xs[j + 1]] = True
            sel &= both
            if sel.sum() < 4:
                continue
            de = delta_e_2000(srgb_to_lab(source_rgb[sel]), srgb_to_lab(built_rgb[sel]))
            out.append({
                "row": i, "col": j,
                "cells": int(sel.sum()),
                "colourDeltaE": round(float(de.mean()), 2),
            })
    out.sort(key=lambda t: -t["colourDeltaE"])
    return out
