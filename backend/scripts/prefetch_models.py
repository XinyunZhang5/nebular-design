"""Download and load both vision models, at image-build time.

Two jobs, and the second is the more valuable one.

**Bake.** The server stops when nobody is using it (Fly scale-to-zero) and boots
again on the next request. If the models are not already on disk, that first
request also pays for ~130 MB of downloads from Hugging Face — thirty seconds of
a blank page, every time the site has been quiet. Baked into the image, a cold
start is just the process starting.

**Verify.** The models are not merely downloaded here, they are constructed the
way the services construct them. `transformers` was pinned at 4.47.1 while this
was developed against 5.x, and the failure mode of that mismatch is an exception
inside a request handler in production. Doing it during `docker build` turns it
into a failed build, which is a thing you find out about before deploying.

Run with the same environment the app uses, so HF_HOME points at the path the
runtime will read from.
"""

import sys

from app.config import get_settings

settings = get_settings()


def main() -> int:
    from transformers import (
        SegformerForSemanticSegmentation,
        SegformerImageProcessor,
        pipeline,
    )

    print(f"→ depth: {settings.depth_model}", flush=True)
    depth = pipeline("depth-estimation", model=settings.depth_model, device="cpu")

    print(f"→ segmentation: {settings.segmentation_model}", flush=True)
    processor = SegformerImageProcessor.from_pretrained(settings.segmentation_model)
    model = SegformerForSemanticSegmentation.from_pretrained(settings.segmentation_model)
    model.eval()

    # A real forward pass on a tiny image. Loading weights proves the checkpoint
    # is readable; only running one proves the processor and the model agree about
    # tensor shapes, which is where a version mismatch actually bites.
    from PIL import Image

    probe = Image.new("RGB", (64, 64), (128, 128, 128))
    depth(probe)
    import torch

    with torch.no_grad():
        model(**processor(images=probe, return_tensors="pt"))

    print("✓ both models load and run on this image", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
