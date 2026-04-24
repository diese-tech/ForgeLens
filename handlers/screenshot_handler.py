import asyncio
from datetime import timezone

import discord

import config
from handlers.match_correlator import merge_extractions
from services import gemini_vision, sheets_service
from utils.uid_parser import extract_uid

REACT_OK      = "✅"
REACT_WARN    = "⚠️"
REACT_UNKNOWN = "❓"
REACT_FAIL    = "❌"

# Mime types accepted for vision analysis
_IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}


async def handle_screenshot_message(message: discord.Message) -> None:
    images = [a for a in message.attachments if _is_image(a)]
    if not images:
        return

    sheet_id = sheets_service.get_active_sheet_id()
    if not sheet_id:
        await message.add_reaction(REACT_WARN)
        await _admin(message, "⚠️ No active season sheet. Run `/newseason` first.")
        return

    draft_id = extract_uid(
        text=message.content,
        filenames=[a.filename for a in images],
    )

    scoreboard: dict | None = None
    details:    dict | None = None
    failed_count = 0
    unknown_count = 0

    for attachment in images:
        raw = await attachment.read()
        mime = attachment.content_type or "image/png"

        try:
            result = await gemini_vision.analyze_image(raw, mime)
        except Exception as e:
            failed_count += 1
            await _admin(message, f"❌ Gemini error on `{attachment.filename}`: {e}")
            continue

        if not result.get("valid"):
            unknown_count += 1
            continue

        stype = result.get("screenshot_type", "")
        if stype == "scoreboard":
            scoreboard = result
        elif stype == "details":
            details = result

    # Nothing usable extracted
    if scoreboard is None and details is None:
        if failed_count > 0:
            await message.add_reaction(REACT_FAIL)
        else:
            await message.add_reaction(REACT_UNKNOWN)
        return

    # Build merged rows
    date = message.created_at.replace(tzinfo=timezone.utc).isoformat()
    game_number = ""  # assigned by submission order; correlator doesn't know game number yet
    rows = merge_extractions(scoreboard, details, draft_id or "", game_number, date)

    partial = _is_partial(details, scoreboard)

    if draft_id:
        await asyncio.to_thread(sheets_service.append_player_stats, sheet_id, rows)
        if partial:
            await message.add_reaction(REACT_WARN)
            await _admin(message, f"⚠️ `{draft_id}` — partial extraction. Some stats may be missing.")
        else:
            await message.add_reaction(REACT_OK)
    else:
        # No UID found — route to Unlinked
        player_names = _player_names(details or scoreboard)
        await asyncio.to_thread(sheets_service.append_unlinked, sheet_id, {
            "timestamp":           date,
            "message_id":          str(message.id),
            "parsed_player_names": ", ".join(player_names),
            "raw_stats_json":      _raw_json(details or scoreboard),
            "notes":               "No UID found in message or filenames",
        })
        await message.add_reaction(REACT_WARN)
        await _admin(
            message,
            f"⚠️ Screenshot posted without a draft ID (message {message.id}). "
            "Stats saved to Unlinked tab. Use `/link uid:GF-XXXX` replying to that message to resolve.",
        )


async def reparse_message(message: discord.Message) -> bool:
    """Re-send all images in message to Gemini and overwrite existing sheet data. Returns True on success."""
    images = [a for a in message.attachments if _is_image(a)]
    if not images:
        return False

    sheet_id = sheets_service.get_active_sheet_id()
    if not sheet_id:
        return False

    # Remove from Unlinked if present, then re-run the full flow
    await asyncio.to_thread(
        sheets_service.remove_unlinked_by_message_id, sheet_id, str(message.id)
    )

    # Clear any existing reactions by the bot
    try:
        me = message.guild.me
        for reaction in message.reactions:
            await reaction.remove(me)
    except discord.HTTPException:
        pass

    await handle_screenshot_message(message)
    return True


# ── Helpers ────────────────────────────────────────────────────────────────

def _is_image(attachment: discord.Attachment) -> bool:
    ct = attachment.content_type or ""
    return any(ct.startswith(m) for m in _IMAGE_MIMES) or attachment.filename.lower().endswith(
        (".png", ".jpg", ".jpeg", ".gif", ".webp")
    )


def _is_partial(details: dict | None, scoreboard: dict | None) -> bool:
    """Return True if either extraction is missing players or has empty stat fields."""
    if details is None or scoreboard is None:
        return True
    all_players = details.get("order_players", []) + details.get("chaos_players", [])
    if len(all_players) < 10:  # 5v5
        return True
    key_stats = ["player_damage", "gpm", "k"]
    return any(p.get(s, "") == "" for p in all_players for s in key_stats)


def _player_names(extraction: dict) -> list[str]:
    players = extraction.get("order_players", []) + extraction.get("chaos_players", [])
    return [p.get("player_name", "") for p in players if p.get("player_name")]


def _raw_json(extraction: dict) -> str:
    import json
    return json.dumps(extraction)


async def _admin(message: discord.Message, text: str) -> None:
    channel = message.guild.get_channel(config.ADMIN_REPORT_CHANNEL_ID)
    if channel:
        await channel.send(text)
