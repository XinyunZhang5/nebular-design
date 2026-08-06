"""Find the building in a photo and throw everything else away.

A depth map covers the whole frame, so without this step the sky, trees, grass
and passing cars all get turned into plates — and because sky is usually the
largest flat region, it dominates the parts list. Segmenting first means the
model is of the building, and the piece count is spent on the building.

Uses SegFormer fine-tuned on ADE20K, which labels every pixel with one of 150
classes. Classes 1 (building), 25 (house), 48 (skyscraper), 84 (tower) and
61 (bridge) are the ones that matter; sky (2), tree (4), grass (9) and water
(21) are the ones that used to eat the budget.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

from app.config import get_settings

settings = get_settings()

_executor = ThreadPoolExecutor(max_workers=1)
# Keyed by model name so the preview harness can hold several sizes at once and
# compare them without a restart. In production only one key is ever populated.
_models: dict[str, tuple] = {}
_model_lock = asyncio.Lock()

# ADE20K class IDs that are part of a structure. Chosen by ID rather than by
# matching class names: "skyscraper" contains the substring "sky", and
# "streetlight" contains "tree", so keyword filtering silently drops buildings
# and keeps foliage.
BUILDING_CLASS_IDS: frozenset[int] = frozenset(
    {
        0,  # wall
        1,  # building
        8,  # windowpane
        14,  # door
        25,  # house
        38,  # railing
        42,  # column
        48,  # skyscraper
        51,  # grandstand
        53,  # stairs
        58,  # screen door
        59,  # stairway
        61,  # bridge
        79,  # hovel
        84,  # tower
        86,  # awning
        88,  # booth
        95,  # bannister
        106,  # canopy
        121,  # step
        140,  # pier
    }
)

# Named only so the diagnostics can report what was discarded and why.
BACKGROUND_CLASS_NAMES = {
    2: "sky",
    4: "tree",
    9: "grass",
    13: "earth",
    16: "mountain",
    17: "plant",
    21: "water",
    26: "sea",
    6: "road",
    11: "sidewalk",
    12: "person",
    20: "car",
    34: "rock",
    46: "sand",
    52: "path",
    60: "river",
    68: "hill",
    72: "palm",
    76: "boat",
    128: "lake",
}

# A stud is part of the building when at least this much of its footprint is.
STUD_COVERAGE_THRESHOLD = 0.5

# Connected blobs smaller than this share of the building are specks — a mislabelled
# roof tile, a sign read as a wall — and only add stray floating plates.
MIN_COMPONENT_SHARE = 0.005


def _load_sync(model_name: str):
    from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

    logger.info("Loading segmentation model: %s", model_name)
    processor = SegformerImageProcessor.from_pretrained(model_name)
    model = SegformerForSemanticSegmentation.from_pretrained(model_name)
    model.eval()
    logger.info("Segmentation model loaded: %s", model_name)
    return model, processor


async def _get_model(model_name: str):
    async with _model_lock:
        if model_name not in _models:
            loop = asyncio.get_event_loop()
            _models[model_name] = await loop.run_in_executor(_executor, _load_sync, model_name)
    return _models[model_name]


def _largest_components(mask: np.ndarray, min_share: float) -> np.ndarray:
    """Drop disconnected specks, keeping every blob above min_share of the total.

    4-connected BFS. Holes are deliberately left alone: you really can see sky
    through the arches of a bridge, and filling those in would be wrong.
    """
    h, w = mask.shape
    total = int(mask.sum())
    if total == 0:
        return mask
    min_size = max(1, int(total * min_share))

    seen = np.zeros_like(mask, dtype=bool)
    keep = np.zeros_like(mask, dtype=bool)

    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            queue = deque([(sy, sx)])
            seen[sy, sx] = True
            cells = []
            while queue:
                y, x = queue.popleft()
                cells.append((y, x))
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((ny, nx))
            if len(cells) >= min_size:
                for y, x in cells:
                    keep[y, x] = True
    return keep


def _segment_sync(model, processor, image: Image.Image) -> dict:
    import torch

    rgb = image.convert("RGB")
    inputs = processor(images=rgb, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)

    # Logits come back at a quarter resolution; ask the processor to put them
    # back onto the original pixel grid before taking the argmax.
    seg = processor.post_process_semantic_segmentation(
        outputs, target_sizes=[(rgb.size[1], rgb.size[0])]
    )[0]
    classes = seg.cpu().numpy().astype(np.int32)

    mask = np.isin(classes, list(BUILDING_CLASS_IDS))
    building_share = float(mask.mean())

    id2label = model.config.id2label
    present = {}
    for cls_id, count in zip(*np.unique(classes, return_counts=True)):
        present[id2label[int(cls_id)]] = round(float(count) / classes.size, 4)
    top = dict(sorted(present.items(), key=lambda kv: -kv[1])[:8])

    return {"mask": mask, "classes": classes, "building_share": building_share, "composition": top}


async def segment_building(image: Image.Image, model_name: str | None = None) -> dict:
    """Return a boolean building mask plus diagnostics about what was in the frame."""
    model, processor = await _get_model(model_name or settings.segmentation_model)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _segment_sync, model, processor, image)


def crop_to_building(
    image: Image.Image, depth: np.ndarray, mask: np.ndarray, padding: float = 0.02
) -> tuple[Image.Image, np.ndarray, np.ndarray]:
    """Trim the frame to the building's bounding box.

    Without this, a building occupying a third of a wide shot gets a third of the
    studs. Cropping first means the whole grid is spent on the subject.

    The depth map usually has its own resolution, so it is resampled to the photo
    before cropping rather than cropped with the photo's pixel coordinates.
    """
    w, h = image.size
    if depth.shape != (h, w):
        depth = np.asarray(
            Image.fromarray(depth.astype(np.float32), mode="F").resize(
                (w, h), Image.Resampling.BILINEAR
            ),
            dtype=np.float32,
        )
    if mask.shape != (h, w):
        mask = (
            np.asarray(
                Image.fromarray(mask.astype(np.uint8) * 255).resize(
                    (w, h), Image.Resampling.NEAREST
                )
            )
            > 127
        )

    ys, xs = np.where(mask)
    if len(ys) == 0:
        logger.warning("No building found; falling back to the whole frame.")
        return image, depth, np.ones((h, w), dtype=bool)

    pad_x, pad_y = int(w * padding), int(h * padding)
    x0 = max(0, int(xs.min()) - pad_x)
    x1 = min(w, int(xs.max()) + 1 + pad_x)
    y0 = max(0, int(ys.min()) - pad_y)
    y1 = min(h, int(ys.max()) + 1 + pad_y)

    return image.crop((x0, y0, x1, y1)), depth[y0:y1, x0:x1], mask[y0:y1, x0:x1]


def clean_stud_mask(stud_mask: np.ndarray) -> np.ndarray:
    """Remove floating specks once the mask is down at stud resolution.

    Done here rather than on the full-size mask because it is the stud grid that
    decides whether a blob becomes one lonely 1x1 plate hanging in mid-air, and
    because a few thousand cells is fast enough to flood-fill in plain Python.
    """
    return _largest_components(stud_mask, MIN_COMPONENT_SHARE)
