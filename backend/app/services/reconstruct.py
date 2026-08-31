"""Single photo -> 3D mesh, with TripoSR.

This is the step that lets the model have a back. `depth.py` answers "how far
away is this pixel", which is all one photograph can say about the surface
facing the camera and nothing at all about the other three sides; the geometry
built from it is a relief. A reconstruction guesses the whole object, and the
guess is good enough at the resolution a brick lattice keeps — 40 studs across
throws away everything finer than a fortieth of the building, which is most of
what the guess gets wrong.

TripoSR rather than the better-known alternatives because of what has to run
here. TRELLIS, InstantMesh and SF3D all reach for compiled CUDA extensions —
sparse convolutions, nvdiffrast, a texture baker — and there is no CUDA on
Apple Silicon. TripoSR is a plain PyTorch transformer with a triplane NeRF head,
so it runs on MPS with an op or two falling back to the CPU, in under ten
seconds. Two edits are vendored in `vendor/triposr` for that: marching cubes via
scikit-image instead of the `torchmcubes` CUDA extension, and rembg made
optional, because the building mask here comes from SegFormer and is better for
the job than a general background remover.

WHY THE IMAGE IS COMPOSITED ONTO GREY

The model was trained on objects cut out onto a neutral field. Handing it a
photograph with its sky and street still attached makes it reconstruct the
street. Segmenting first and compositing the building onto 0.5 grey is the
input it expects, and it is the same mask the rest of the pipeline already uses.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

# Before torch is imported anywhere in the process, which is why it is here at
# module scope and not inside `_device()`. A couple of ops in the image
# tokeniser — bicubic `interpolate` among them — have no MPS kernel, and PyTorch
# reads this flag when it brings the MPS backend up, not when it hits the
# missing op. Set it late and the forward pass raises instead of falling back.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

VENDOR = Path(__file__).resolve().parents[2] / "vendor" / "triposr"

# One at a time. The model holds about 1.7 GB of weights and a second concurrent
# forward pass doubles that; the queue is cheaper than the swap.
_executor = ThreadPoolExecutor(max_workers=1)
_model = None
_model_lock = asyncio.Lock()

# How much of the frame the subject should fill. TripoSR's own examples sit at
# this and it is sensitive to it: fill the frame and the reconstruction loses
# the silhouette's edges, shrink it and the resolution goes into empty grey.
FOREGROUND_RATIO = 0.85

# Marching cubes resolution. The lattice is 40-96 studs across, so 256 is
# already finer than anything that survives voxelisation; 512 quadruples the
# isosurface cost to produce detail that is immediately quantised away.
MC_RESOLUTION = 256


def _device() -> str:
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _load_sync():
    if str(VENDOR) not in sys.path:
        sys.path.insert(0, str(VENDOR))
    from tsr.system import TSR

    logger.info("Loading TripoSR: %s", settings.reconstruction_model)
    model = TSR.from_pretrained(
        settings.reconstruction_model, config_name="config.yaml", weight_name="model.ckpt"
    )
    model.renderer.set_chunk_size(8192)
    model.to(_device())
    logger.info("TripoSR loaded on %s", _device())
    return model


async def _get_model():
    global _model
    async with _model_lock:
        if _model is None:
            loop = asyncio.get_event_loop()
            _model = await loop.run_in_executor(_executor, _load_sync)
    return _model


def _compose(image: Image.Image, mask: np.ndarray | None) -> Image.Image:
    """Cut the building out and centre it on grey, the way TripoSR expects."""
    if str(VENDOR) not in sys.path:
        sys.path.insert(0, str(VENDOR))
    from tsr.utils import resize_foreground

    rgb = np.asarray(image.convert("RGB"))
    if mask is None:
        alpha = np.full(rgb.shape[:2], 255, dtype=np.uint8)
    else:
        resized = Image.fromarray((mask.astype(np.uint8) * 255)).resize(
            image.size, Image.NEAREST
        )
        alpha = np.asarray(resized)
    fg = resize_foreground(
        Image.fromarray(np.dstack([rgb, alpha]), "RGBA"), FOREGROUND_RATIO
    )
    a = np.asarray(fg).astype(np.float32) / 255.0
    grey = a[:, :, :3] * a[:, :, 3:4] + (1 - a[:, :, 3:4]) * 0.5
    return Image.fromarray((grey * 255).astype(np.uint8))


def _reconstruct_sync(model, image: Image.Image):
    import torch

    device = _device()
    with torch.no_grad():
        codes = model(image, device=device)
        return model.extract_mesh(codes, True, resolution=MC_RESOLUTION)[0]


async def reconstruct(image: Image.Image, mask: np.ndarray | None = None):
    """Photo (plus its building mask) -> a trimesh with vertex colours."""
    model = await _get_model()
    prepared = _compose(image, mask)
    loop = asyncio.get_event_loop()
    mesh = await loop.run_in_executor(_executor, _reconstruct_sync, model, prepared)
    logger.info(
        "reconstruct: %d vertices, %d faces, watertight=%s",
        len(mesh.vertices), len(mesh.faces), mesh.is_watertight,
    )
    return mesh
