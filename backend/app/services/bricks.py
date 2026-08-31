"""AI brick matching service — calls Claude with image + depth data."""

import asyncio
import base64
import io
import logging
from typing import Any

import anthropic
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# The vision API rejects any single image whose base64 payload exceeds 10 MB, and
# base64 inflates raw bytes by about a third — so the raw image has to stay under
# roughly 7.5 MB. We aim well below that.
#
# Separately, claude-sonnet-4-6 sits in the standard resolution tier, which downscales
# anything longer than 1568 px on its long edge before the model ever sees it. Shrinking
# to that edge here therefore costs no fidelity — it only avoids shipping bytes the API
# would discard. Raise to 2576 if you move to a Claude 4.7-or-later model.
CLAUDE_MAX_EDGE = 1568
CLAUDE_MAX_BYTES = 4 * 1024 * 1024


def _prepare_for_claude(image_bytes: bytes, media_type: str) -> tuple[bytes, str]:
    """Shrink an upload to something the vision API will accept.

    Returns the original bytes untouched when they already fit, so small uploads keep
    their encoding instead of paying for a needless re-compress.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size
    except Exception:
        logger.warning("Could not decode upload for resizing; sending it unchanged.")
        return image_bytes, media_type

    if max(width, height) <= CLAUDE_MAX_EDGE and len(image_bytes) <= CLAUDE_MAX_BYTES:
        return image_bytes, media_type

    image = image.convert("RGB")  # JPEG carries no alpha channel
    if max(width, height) > CLAUDE_MAX_EDGE:
        scale = CLAUDE_MAX_EDGE / max(width, height)
        image = image.resize(
            (max(1, round(width * scale)), max(1, round(height * scale))),
            Image.Resampling.LANCZOS,
        )

    # Step the quality down until it fits. The first pass wins for almost every photo.
    data = image_bytes
    for quality in (85, 70, 55, 40):
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        if len(data) <= CLAUDE_MAX_BYTES:
            logger.info(
                "Prepared image for Claude: %dx%d %.1fMB -> %dx%d %.1fMB (quality %d)",
                width, height, len(image_bytes) / 1e6,
                image.width, image.height, len(data) / 1e6, quality,
            )
            return data, "image/jpeg"

    logger.warning(
        "Image is still %.1fMB after compression; sending it and letting the API decide.",
        len(data) / 1e6,
    )
    return data, "image/jpeg"

# The shape of the answer, declared to the API instead of described in the
# prompt and parsed out of prose afterwards.
#
# The prompt used to end with "Return ONLY a JSON object" and the reply was read
# by finding the first { and the last } and calling json.loads on what lay
# between. That works until the model writes a building's name with a quotation
# mark in it, or an apostrophe the encoder handles differently, and then it does
# not work at all:
#
#     Claude description failed: Expecting ',' delimiter: line 16 column 71
#
# There is no error surfaced from that — describe_build returns {} and the build
# is stored as "Untitled Structure" with no description, looking for all the
# world like a model that had nothing to say. Declaring the schema makes the
# response a validated object, so this failure cannot happen.
DESCRIBE_TOOL: dict[str, Any] = {
    "name": "record_description",
    "description": "Record the name, description and band titles for a finished LEGO model.",
    "input_schema": {
        "type": "object",
        "properties": {
            "buildingName": {
                "type": "string",
                "description": "The building's name if recognised, otherwise a descriptive name.",
            },
            "description": {
                "type": "string",
                "description": (
                    "Two or three sentences on what the building is and what makes it "
                    "distinctive as a three-dimensional model."
                ),
            },
            "levelNotes": {
                "type": "array",
                "description": "One entry per band of courses, numbered 1 upward from the ground.",
                "items": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "integer"},
                        "title": {"type": "string", "description": "A short phrase for this band."},
                    },
                    "required": ["level", "title"],
                },
            },
        },
        "required": ["buildingName", "description", "levelNotes"],
    },
}

SYSTEM_PROMPT = """You are an architecture writer for a LEGO design tool.

A build plan has ALREADY been computed from the photograph by a geometry
pipeline: every brick, its position, its colour and the total piece count are
fixed and correct. You are not designing anything and you are not checking
anything. Your job is the part a geometry pipeline cannot do — recognising the
building and writing about it.

Rules:
- NEVER state a part number, a quantity, a piece count or a colour count. Those
  are supplied to you as facts and are rendered separately.
- If you recognise the specific building, name it. If you do not, describe it by
  type and style instead of guessing a landmark.
- Write plainly. No marketing voice, no exclamation marks.

Answer by calling the record_description tool."""

USER_PROMPT_TEMPLATE = """Here is the photograph a LEGO model was generated from.

IMPORTANT — what actually got built:
This is a free-standing model, built in courses of bricks on a plate floor, not a
picture. Seen from the front it reproduces the photograph; seen from the side it
has real depth, because parts of the subject that were nearer the camera stand
further forward. The back is a flat plane — a single photograph says nothing
about what is behind the subject, so nothing was invented there.

The background was segmented away first. Sky, trees, grass, water, roads, people
and vehicles are NOT built: there is simply no brick there, so the model's
outline is the building's outline. Do not describe sky, water or landscape.
Colours in the palette that look like sky or foliage come from the building
itself — painted ironwork, weathered stone, glazing.

Facts about the model (already computed — do not restate the numbers):
- {grid_w} studs wide, {courses} courses tall, {depth} studs deep
- {building_cells} of {cells} cells are building; the rest is open air
- {visible} bricks make up the facade, over {hidden} that form the structure behind it
- Palette actually used: {palette}

The model is built bottom-up in {bands} bands of courses. Give exactly {bands}
entries in levelNotes, numbered 1 upward: band 1 is the ground, band {bands} the
top of the building."""


async def describe_build(
    image_bytes: bytes,
    content_type: str,
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Name and describe a plan that has already been computed.

    Returns only prose. The caller merges it into the computed plan; nothing here
    is allowed to change a part, a quantity or a coordinate. When the API key is
    missing or the call fails, the plan simply goes out without the prose rather
    than with invented numbers — the failure mode that produced the old fictional
    parts lists.

    Three fields, because three fields are all the UI renders: the title, the
    paragraph under it, and one heading per band of courses. This used to also ask
    for architecturalStyle, recognised, tips and a sentence per band; all four were
    stored on the project and read by nothing, so every build paid for output
    tokens that no one would ever see.
    """
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping description")
        return {}

    media_type_map = {
        "image/jpeg": "image/jpeg", "image/jpg": "image/jpeg", "image/png": "image/png",
        "image/gif": "image/gif", "image/webp": "image/webp",
    }
    media_type = media_type_map.get(content_type, "image/jpeg")
    payload, media_type = await asyncio.to_thread(_prepare_for_claude, image_bytes, media_type)
    b64 = base64.b64encode(payload).decode()

    grid = plan.get("grid", {})
    # Bands, not courses: the steps are bands, so the notes have to be too, or the
    # merge in the router silently drops every note that has no step to land on.
    bands = len([s for s in plan.get("steps", []) if s.get("level")])
    prompt = USER_PROMPT_TEMPLATE.format(
        grid_w=grid.get("width", "?"),
        courses=grid.get("courses", "?"),
        depth=grid.get("depth", "?"),
        bands=bands or "?",
        cells=grid.get("cells", "?"),
        building_cells=grid.get("buildingCells", "?"),
        visible=plan.get("visiblePieceCount", "?"),
        hidden=plan.get("hiddenPieceCount", "?"),
        palette=", ".join(c["name"] for c in plan.get("colorPalette", [])) or "unknown",
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        response = await asyncio.to_thread(
            lambda: client.messages.create(
                model=settings.claude_model,
                # A name, a paragraph and eight headings measured 772 tokens, so
                # 800 was one long description away from being truncated. Tall
                # buildings get more bands, so leave real headroom; the cap costs
                # nothing unless it is reached.
                max_tokens=1200,
                system=SYSTEM_PROMPT,
                tools=[DESCRIBE_TOOL],
                # Forced, so the reply is the object and never a sentence about
                # the object.
                tool_choice={"type": "tool", "name": DESCRIBE_TOOL["name"]},
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64",
                                                     "media_type": media_type, "data": b64}},
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
        )
        # Not content[0]: a response can open with a thinking block, and reading
        # the tool call off the wrong block raises. That failure looked exactly
        # like a model that had nothing to say — the build came back named
        # "Untitled Structure" with no error surfaced anywhere the user could see.
        data = next(
            (
                block.input
                for block in response.content
                if getattr(block, "type", None) == "tool_use"
                and block.name == DESCRIBE_TOOL["name"]
            ),
            None,
        )
        if data is None:
            raise ValueError("Claude did not call the description tool")
    except Exception as exc:
        logger.exception("Claude description failed: %s", exc)
        return {}

    # Keep only the prose fields. Anything else the model volunteered — a parts
    # list, a piece count, a "corrected" quantity — is dropped on the floor.
    return {k: data[k] for k in ("buildingName", "description", "levelNotes") if k in data}
