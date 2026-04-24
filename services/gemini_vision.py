import json
import re

from google import genai
from google.genai import types

import config

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


_PROMPT = """
You are analyzing a Smite 2 post-match screenshot. There are two possible screen types.

SCREEN TYPE 1 — SCOREBOARD
Contains player names, god names, role icons (small icons left of the god portrait), Level, K/D/A, Gold, and Items.
Role icons map as follows:
- Axe / sword icon → Solo
- Leaf / grass icon → Jungle
- Diamond shape → Middle
- Shield with plus sign → Support
- Arrowhead / arrow icon → Carry

SCREEN TYPE 2 — DETAILS
Contains per-player columns with labeled stat rows. This is the primary extraction target.
Extract ALL of the following per player:
KDA (split into K, D, A), GPM, Player Damage, Minion Damage, Jungle Damage,
Structure Damage, Damage Taken, Damage Mitigated, Self Healing, Ally Healing, Wards Placed.
The left side is Order (blue team), the right side is Chaos (red team).
Gold star icons highlight the highest value per row — extract the raw number only, ignore the star.

RESPONSE RULES:
1. Return JSON only — no markdown, no explanation, no code fences.
2. If you are less than 70% confident this is a Smite 2 match screen, return exactly: {"valid": false}
3. Always include "valid": true when you can extract data.
4. Always include "screenshot_type": "scoreboard" or "screenshot_type": "details".

FOR SCOREBOARD responses, return:
{
  "valid": true,
  "screenshot_type": "scoreboard",
  "order_players": [
    {"player_name": "", "god": "", "role": "", "level": "", "k": "", "d": "", "a": "", "gold": ""}
  ],
  "chaos_players": [
    {"player_name": "", "god": "", "role": "", "level": "", "k": "", "d": "", "a": "", "gold": ""}
  ]
}

FOR DETAILS responses, return:
{
  "valid": true,
  "screenshot_type": "details",
  "order_players": [
    {
      "player_name": "",
      "k": "", "d": "", "a": "",
      "gpm": "",
      "player_damage": "", "minion_damage": "", "jungle_damage": "", "structure_damage": "",
      "damage_taken": "", "damage_mitigated": "",
      "self_healing": "", "ally_healing": "",
      "wards_placed": ""
    }
  ],
  "chaos_players": [ /* same shape as order_players */ ]
}

Use empty string "" for any value you cannot read clearly.
""".strip()


async def analyze_image(image_bytes: bytes, mime_type: str = "image/png") -> dict:
    """
    Send a screenshot to Gemini and return structured extraction as a dict.
    Returns {"valid": false} if the image is not a recognizable Smite 2 screen.
    Raises on API errors (caller handles retries / reactions).
    """
    client = _get_client()

    response = await _run_in_thread(client, image_bytes, mime_type)
    return _parse_response(response)


def _run_in_thread_sync(client: genai.Client, image_bytes: bytes, mime_type: str):
    return client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            types.Part.from_text(text=_PROMPT),
        ],
    )


async def _run_in_thread(client: genai.Client, image_bytes: bytes, mime_type: str):
    import asyncio
    return await asyncio.to_thread(_run_in_thread_sync, client, image_bytes, mime_type)


def _parse_response(response) -> dict:
    raw = response.text.strip()
    # Strip markdown code fences if Gemini includes them despite instructions
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"valid": False, "error": "unparseable response", "raw": raw}
