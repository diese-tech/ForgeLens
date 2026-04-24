import asyncio
import json
from datetime import timezone

import discord

import config
from services import sheets_service
from utils.uid_parser import extract_uid


async def handle_json_message(message: discord.Message) -> None:
    """Process a new message in the JSON drop channel."""
    json_attachments = [a for a in message.attachments if a.filename.endswith(".json")]
    if not json_attachments:
        return

    sheet_id = sheets_service.get_active_sheet_id()
    if not sheet_id:
        await _admin(message, "⚠️ No active season sheet. Run `/newseason` first.")
        return

    for attachment in json_attachments:
        await _process_attachment(message, attachment, sheet_id)


async def _process_attachment(
    message: discord.Message,
    attachment: discord.Attachment,
    sheet_id: str,
) -> None:
    raw_bytes = await attachment.read()

    try:
        data = json.loads(raw_bytes)
    except json.JSONDecodeError:
        await _admin(message, f"❌ Could not parse `{attachment.filename}` — invalid JSON.")
        return

    if "draft_id" not in data:
        await _admin(
            message,
            f"❌ `{attachment.filename}` is missing a `draft_id` field. Is this a GodForge file?",
        )
        return

    # Prefer the draft_id from JSON content; fall back to filename
    draft_id = data.get("draft_id") or extract_uid(filenames=[attachment.filename])
    if not draft_id:
        await _admin(message, f"❌ Could not determine draft_id from `{attachment.filename}`.")
        return

    submitted_at = message.created_at.replace(tzinfo=timezone.utc).isoformat()
    games = data.get("games") or [data]  # support flat (single-game) or games-array format

    for i, game in enumerate(games, start=1):
        row = {
            "draft_id":      draft_id,
            "game_number":   game.get("game_number", i),
            "submitted_at":  submitted_at,
            "blue_captain":  data.get("blue_captain", ""),
            "red_captain":   data.get("red_captain", ""),
            "blue_picks":    _join(game.get("blue_picks", [])),
            "red_picks":     _join(game.get("red_picks", [])),
            "blue_bans":     _join(game.get("blue_bans", [])),
            "red_bans":      _join(game.get("red_bans", [])),
            "fearless_pool": _join(game.get("fearless_pool", [])),
            "game_status":   game.get("status", game.get("game_status", "Unknown")),
            "winner":        "TBD",
            "series_score":  "TBD",
        }
        await asyncio.to_thread(sheets_service.append_match_log, sheet_id, row)

    game_word = "game" if len(games) == 1 else "games"
    await _admin(
        message,
        f"✅ `{draft_id}` — {len(games)} {game_word} logged to Match Log.",
    )


def _join(values: list) -> str:
    return ", ".join(str(v) for v in values) if values else ""


async def _admin(message: discord.Message, text: str) -> None:
    channel = message.guild.get_channel(config.ADMIN_REPORT_CHANNEL_ID)
    if channel:
        await channel.send(text)
