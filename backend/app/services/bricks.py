"""AI brick matching service — calls Claude with image + depth data."""

import base64
import json
import logging
from typing import Any

import anthropic

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MOCK_RESULT = {
    "buildingName": "Classic Town House",
    "difficulty": "Intermediate",
    "estimatedPieceCount": 312,
    "estimatedTime": "3-4 hours",
    "colorPalette": ["White", "Light Bluish Gray", "Dark Bluish Gray", "Tan"],
    "bricks": [
        {"name": "2×4 Brick", "partId": "3001", "color": "White", "quantity": 48, "description": "Main wall sections"},
        {"name": "2×2 Brick", "partId": "3003", "color": "White", "quantity": 36, "description": "Corner joints"},
        {"name": "1×4 Brick", "partId": "3010", "color": "Light Bluish Gray", "quantity": 30, "description": "Window lintels and sills"},
        {"name": "1×2 Plate", "partId": "3023", "color": "White", "quantity": 44, "description": "Thin floor layers"},
        {"name": "2×4 Plate", "partId": "3020", "color": "Tan", "quantity": 20, "description": "Foundation plates"},
        {"name": "1×2 Slope 45°", "partId": "3040", "color": "Dark Bluish Gray", "quantity": 28, "description": "Roof edge slopes"},
        {"name": "2×4 Slope 45°", "partId": "3037", "color": "Dark Bluish Gray", "quantity": 18, "description": "Main roof panels"},
        {"name": "1×2 Tile", "partId": "3069b", "color": "Light Bluish Gray", "quantity": 32, "description": "Window and floor tiles"},
        {"name": "Trans-Clear 1×2 Plate", "partId": "3023t", "color": "Transparent", "quantity": 24, "description": "Window glass"},
        {"name": "Door Frame 1×4×6", "partId": "60596", "color": "White", "quantity": 2, "description": "Main entrance frame"},
        {"name": "Window Frame 1×2×2", "partId": "60592", "color": "White", "quantity": 8, "description": "Window frames"},
        {"name": "1×1 Round Plate", "partId": "6141", "color": "Dark Bluish Gray", "quantity": 20, "description": "Detail accents"},
    ],
    "steps": [
        {
            "step": 1,
            "title": "Foundation",
            "description": "Lay 2×4 Tan Plates across a 16×16 baseplate to form the ground floor.",
            "bricksUsed": ["2×4 Plate (Tan) ×10"],
            "tip": "Use a flat surface — gaps in the foundation affect all layers above.",
        },
        {
            "step": 2,
            "title": "Ground Floor Walls",
            "description": "Stack White 2×4 and 2×2 Bricks four courses high, offsetting joints each row.",
            "bricksUsed": ["2×4 Brick (White) ×20", "2×2 Brick (White) ×18"],
            "tip": "Stagger bricks by 2 studs per row for structural integrity.",
        },
        {
            "step": 3,
            "title": "Door & Window Openings",
            "description": "Insert Door Frame and Window Frames into openings. Cap each with a 1×4 Gray lintel.",
            "bricksUsed": ["Door Frame 1×4×6 ×2", "Window Frame 1×2×2 ×8", "1×4 Brick (Light Bluish Gray) ×8"],
        },
        {
            "step": 4,
            "title": "Upper Floor",
            "description": "Continue wall courses for the second storey. Place Trans-Clear plates flush with window openings.",
            "bricksUsed": ["2×4 Brick (White) ×28", "1×2 Plate (White) ×22", "Trans-Clear 1×2 ×24"],
        },
        {
            "step": 5,
            "title": "Roof Structure",
            "description": "Build the pitched roof using 2×4 Slope 45° bricks along both sides of the ridge.",
            "bricksUsed": ["2×4 Slope 45° (Dark Gray) ×18", "1×2 Slope 45° (Dark Gray) ×28"],
            "tip": "Slopes on opposite sides should meet exactly at the ridge — check alignment before gluing.",
        },
        {
            "step": 6,
            "title": "Finishing Details",
            "description": "Apply 1×2 Tiles on sills and floors. Add 1×1 Round Plates as accent studs.",
            "bricksUsed": ["1×2 Tile (Light Gray) ×32", "1×1 Round Plate (Dark Gray) ×20"],
        },
    ],
}

SYSTEM_PROMPT = """You are a professional LEGO Master Builder AI with expert knowledge of the complete LEGO parts catalog.
Your role is to analyze building photographs and produce accurate, buildable LEGO construction plans.
Always use real LEGO part names, official part IDs, and LEGO color names from the standard palette.
Return ONLY a single JSON object — no markdown fences, no explanatory text before or after."""

USER_PROMPT_TEMPLATE = """Analyze the provided building image and the accompanying 3D depth analysis data to generate a detailed LEGO build plan.

DEPTH ANALYSIS DATA:
{depth_json}

Based on the visual content AND the depth data (which reveals the 3D structure, layer depth distribution, and geometric complexity), produce a JSON object with this exact shape:
{{
  "buildingName": "descriptive name for this structure",
  "difficulty": "Beginner" | "Intermediate" | "Expert",
  "estimatedPieceCount": <integer>,
  "estimatedTime": "X–Y hours",
  "colorPalette": ["LEGO Color 1", "LEGO Color 2", ...],
  "bricks": [
    {{
      "name": "Official LEGO part name (e.g. '2×4 Brick')",
      "partId": "official part number (e.g. '3001')",
      "color": "official LEGO color name",
      "quantity": <integer>,
      "description": "where and how this piece is used in the build"
    }}
  ],
  "steps": [
    {{
      "step": <integer>,
      "title": "short phase name",
      "description": "clear, actionable instruction for this step",
      "bricksUsed": ["Part Name (Color) ×qty", ...],
      "tip": "optional builder tip (omit key if not needed)"
    }}
  ]
}}

Rules:
- Include 10–16 distinct brick types proportional to the depth complexity data
- Include 5–8 assembly steps in logical build order (foundation → walls → openings → upper floors → roof → details)
- Use only real, purchasable LEGO colors (White, Black, Red, Blue, Yellow, Tan, etc.)
- Let the depth layer distribution guide the quantity ratio between structural and detail pieces
- estimatedPieceCount must equal the sum of all brick quantities"""


async def analyze_image(image_bytes: bytes, content_type: str, depth_data: dict[str, Any]) -> dict[str, Any]:
    """Analyze an image with Claude vision + depth data and return a LEGO build plan."""
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — returning mock data")
        return MOCK_RESULT

    media_type_map = {
        "image/jpeg": "image/jpeg",
        "image/jpg": "image/jpeg",
        "image/png": "image/png",
        "image/gif": "image/gif",
        "image/webp": "image/webp",
    }
    media_type = media_type_map.get(content_type, "image/jpeg")
    b64 = base64.b64encode(image_bytes).decode()
    depth_json = json.dumps(depth_data, indent=2)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": USER_PROMPT_TEMPLATE.format(depth_json=depth_json),
                        },
                    ],
                }
            ],
        )

        raw = response.content[0].text if response.content else ""
        # Extract JSON even if Claude adds any surrounding text
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found in Claude response")
        return json.loads(raw[start:end])

    except Exception as exc:
        logger.exception("Claude brick analysis failed: %s", exc)
        return MOCK_RESULT
