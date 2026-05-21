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


def _run_depth_sync(pipeline_obj, image_bytes: bytes) -> dict[str, Any]:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # Resize to fixed resolution for consistent processing
    image_resized = image.resize((640, 480))

    result = pipeline_obj(image_resized)
    depth_array = np.array(result["depth"], dtype=np.float32)

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


async def estimate_depth(image_bytes: bytes) -> dict[str, Any]:
    """Public API: estimate depth from raw image bytes."""
    if not settings.enable_depth_estimation:
        return {"skipped": True, "reason": "ENABLE_DEPTH_ESTIMATION=false"}

    try:
        pipe = await _get_pipeline()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _run_depth_sync, pipe, image_bytes)
    except Exception as exc:
        logger.exception("Depth estimation failed: %s", exc)
        return {"error": str(exc), "fallback": True}
