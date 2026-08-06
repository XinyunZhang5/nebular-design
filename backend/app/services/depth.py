"""2D → 3D depth estimation using DepthAnything V2.

Loads the model lazily on first call. Runs in a thread pool so it
never blocks the async event loop.
"""

import io
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_executor = ThreadPoolExecutor(max_workers=2)
_pipeline = None
_pipeline_lock = asyncio.Lock()


def _load_pipeline_sync():
    from transformers import pipeline as hf_pipeline
    logger.info("Loading DepthAnything model: %s", settings.depth_model)
    pipe = hf_pipeline(
        "depth-estimation",
        model=settings.depth_model,
        device="cpu",
    )
    logger.info("DepthAnything model loaded successfully.")
    return pipe


async def _get_pipeline():
    global _pipeline
    async with _pipeline_lock:
        if _pipeline is None:
            loop = asyncio.get_event_loop()
            _pipeline = await loop.run_in_executor(_executor, _load_pipeline_sync)
    return _pipeline


def _depth_array_sync(pipeline_obj, image: Image.Image, long_edge: int = 1024) -> np.ndarray:
    """Run the model and hand back the depth map itself.

    Larger values are nearer — the model predicts inverse depth, so this maps
    straight onto "how far a stud sticks out" with no inversion needed.

    Aspect ratio is preserved. The old fixed 640x480 resize distorted every photo
    that was not 4:3, which skewed the relief before anything downstream saw it.
    """
    w, h = image.size
    if w >= h:
        size = (long_edge, max(1, round(long_edge * h / w)))
    else:
        size = (max(1, round(long_edge * w / h)), long_edge)
    result = pipeline_obj(image.convert("RGB").resize(size, Image.Resampling.LANCZOS))
    return np.array(result["depth"], dtype=np.float32)


def _stats_from_array(depth_array: np.ndarray) -> dict[str, Any]:
    """Summary statistics kept for the projects table and for display.

    These are a description of the depth map, not a substitute for it — the map
    itself is what services/legolize.py turns into plate heights.
    """
    h, w = depth_array.shape
    d_min, d_max = float(depth_array.min()), float(depth_array.max())
    normalized = (depth_array - d_min) / (d_max - d_min + 1e-8)

    # Depth layer distribution (5 bands: near → far)
    n_layers = 5
    distribution = [
        float(np.mean((normalized >= i / n_layers) & (normalized < (i + 1) / n_layers)))
        for i in range(n_layers)
    ]

    # Edge / structural complexity
    gy, gx = np.gradient(normalized)
    edge_strength = float(np.sqrt(gx**2 + gy**2).mean())

    foreground_ratio = float(np.mean(normalized < 0.3))
    background_ratio = float(np.mean(normalized > 0.7))

    if foreground_ratio > 0.35:
        zone = "foreground"
    elif background_ratio > 0.35:
        zone = "background"
    else:
        zone = "midground"

    # Estimate geometric complexity (coefficient of variation)
    cv = float(np.std(normalized) / (np.mean(normalized) + 1e-8))

    return {
        "width": w,
        "height": h,
        "depth_range_raw": round(d_max - d_min, 4),
        "mean_depth": round(float(normalized.mean()), 4),
        "depth_variance": round(float(normalized.var()), 4),
        "edge_strength": round(edge_strength, 4),
        "geometric_complexity": round(cv, 4),
        "layer_distribution": [round(x, 4) for x in distribution],
        "foreground_ratio": round(foreground_ratio, 4),
        "background_ratio": round(background_ratio, 4),
        "dominant_depth_zone": zone,
    }


async def estimate_depth_map(image: Image.Image, long_edge: int = 1024) -> np.ndarray:
    """Public API: the depth map itself, for callers that build geometry from it."""
    pipe = await _get_pipeline()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _depth_array_sync, pipe, image, long_edge)


async def estimate_depth_with_map(
    image: Image.Image, long_edge: int = 1024
) -> tuple[dict[str, Any], np.ndarray]:
    """Both the summary statistics and the map, from a single forward pass.

    The upload route needs the stats for the database and the map for the
    geometry; running the model twice to get them would double the slowest step
    in the request.
    """
    depth_array = await estimate_depth_map(image, long_edge)
    return _stats_from_array(depth_array), depth_array


async def estimate_depth(image_bytes: bytes) -> dict[str, Any]:
    """Public API: depth summary statistics from raw image bytes."""
    if not settings.enable_depth_estimation:
        return {"skipped": True, "reason": "ENABLE_DEPTH_ESTIMATION=false"}

    try:
        image = Image.open(io.BytesIO(image_bytes))
        depth_array = await estimate_depth_map(image)
        return _stats_from_array(depth_array)
    except Exception as exc:
        logger.exception("Depth estimation failed: %s", exc)
        return {"error": str(exc), "fallback": True}
