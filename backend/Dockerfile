# syntax=docker/dockerfile:1
#
# Nebular Design — backend image.
#
# Two things drive every decision in here:
#
#   1. The machine sleeps. Fly stops it when nobody is using the site, which is
#      what makes this cost about a dollar a month instead of eleven. The price
#      is that the *next* visitor waits for a cold start, so anything that can be
#      done at build time is done at build time — most of all the model weights,
#      which would otherwise be a 130 MB download on the first request after a
#      quiet hour.
#
#   2. Layers are cached in the order they are written. Requirements are copied
#      and installed before the source, so editing a Python file re-runs neither
#      pip nor the model download.

FROM python:3.12-slim

# HF_HOME must be set before anything downloads, and must match at runtime, or
# the weights baked below land in one directory and are looked for in another —
# which is invisible until the first cold start takes thirty seconds.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # Running `python scripts/x.py` puts scripts/ on the path, not /app — so the
    # prefetch step below could not import the app package it reads settings from.
    PYTHONPATH=/app \
    HF_HOME=/opt/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1

WORKDIR /app

# libgomp is OpenMP, which torch links against; the slim image does not have it
# and the failure is an ImportError at the first `import torch`. Nothing else
# here needs a compiler — every dependency ships a manylinux wheel.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The user is created here rather than at the end, and it is not cosmetic
# ordering. A layer records whole files, not diffs — so `chown -R` over the model
# cache after it was written stores a second copy of all 114 MB of it, and the
# image carries both. Owning the directories while they are still empty costs
# nothing. `uploads` has to exist before the drop too: StaticFiles mounts it at
# startup, and the local-storage fallback writes into it if object storage is
# ever unconfigured.
RUN useradd --create-home --uid 10001 nebular \
 && mkdir -p /app/uploads /opt/huggingface \
 && chown -R nebular:nebular /app /opt/huggingface
USER nebular

# The app package is needed for its settings (which model names to fetch), so
# the prefetch cannot come before this copy — but it is its own layer, so a
# change to a router does not re-download 130 MB of weights.
COPY --chown=nebular:nebular app ./app
COPY --chown=nebular:nebular scripts ./scripts
COPY --chown=nebular:nebular run.py .

RUN python scripts/prefetch_models.py

EXPOSE 8000

# run.py, not uvicorn directly: it reads $PORT and switches the reloader off
# outside development. Invoking uvicorn here would silently bypass both.
CMD ["python", "run.py"]
