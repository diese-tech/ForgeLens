import json
from datetime import datetime, timezone
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

import config

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

ACTIVE_SEASON_FILE = "active_season.json"

MATCH_LOG_HEADERS = [
    "Draft ID", "Game Number", "Submitted At",
    "Blue Captain", "Red Captain",
    "Blue Picks", "Red Picks",
    "Blue Bans", "Red Bans",
    "Fearless Pool", "Game Status", "Winner", "Series Score",
]

PLAYER_STATS_HEADERS = [
    "Draft ID", "Game Number", "Date",
    "Player Name", "God", "Role", "Team",
    "K", "D", "A", "GPM",
    "Player Damage", "Minion Damage", "Jungle Damage", "Structure Damage",
    "Damage Taken", "Damage Mitigated", "Self Healing", "Ally Healing",
    "Wards Placed", "Win",
]

UNLINKED_HEADERS = [
    "Timestamp", "Discord Message ID", "Parsed Player Names",
    "Raw Stats JSON", "Notes",
]


def _credentials():
    return service_account.Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
    )


def _sheets():
    return build("sheets", "v4", credentials=_credentials())


def _drive():
    return build("drive", "v3", credentials=_credentials())


# ── Active season persistence ──────────────────────────────────────────────

def get_active_season() -> dict | None:
    if not Path(ACTIVE_SEASON_FILE).exists():
        return None
    with open(ACTIVE_SEASON_FILE) as f:
        return json.load(f)


def get_active_sheet_id() -> str | None:
    season = get_active_season()
    return season["sheet_id"] if season else None


def _save_active_season(sheet_id: str, season_name: str) -> None:
    with open(ACTIVE_SEASON_FILE, "w") as f:
        json.dump({"sheet_id": sheet_id, "season_name": season_name}, f)


# ── Season creation ────────────────────────────────────────────────────────

def create_season_sheet(season_name: str, drive_folder_id: str | None = None) -> str:
    """Create a new season spreadsheet with all four tabs. Returns spreadsheet ID."""
    sheets = _sheets()
    now = _now()

    spreadsheet = sheets.spreadsheets().create(body={
        "properties": {"title": f"{config.LEAGUE_SLUG} — {season_name}"},
        "sheets": [
            {"properties": {"title": "Match Log",     "index": 0}},
            {"properties": {"title": "Player Stats",  "index": 1}},
            {"properties": {"title": "Unlinked",      "index": 2}},
            {"properties": {"title": "Season Config", "index": 3}},
        ],
    }).execute()

    sheet_id = spreadsheet["spreadsheetId"]

    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={"valueInputOption": "RAW", "data": [
            {"range": "Match Log!A1",     "values": [MATCH_LOG_HEADERS]},
            {"range": "Player Stats!A1",  "values": [PLAYER_STATS_HEADERS]},
            {"range": "Unlinked!A1",      "values": [UNLINKED_HEADERS]},
            {"range": "Season Config!A1", "values": [
                ["Field", "Value"],
                ["Active Season Name",  season_name],
                ["Sheet Created",       now],
                ["Last Updated",        now],
                ["Total Games Logged",  "0"],
                ["Bot Version",         "1.0.0"],
            ]},
        ]},
    ).execute()

    if drive_folder_id:
        drive = _drive()
        parents = drive.files().get(fileId=sheet_id, fields="parents").execute().get("parents", [])
        drive.files().update(
            fileId=sheet_id,
            addParents=drive_folder_id,
            removeParents=",".join(parents),
            fields="id,parents",
        ).execute()

    _save_active_season(sheet_id, season_name)
    return sheet_id


def create_drive_folder(folder_name: str, parent_id: str | None = None) -> str:
    """Create a Drive folder (optionally nested inside parent_id) and return its ID."""
    body = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]
    return _drive().files().create(body=body, fields="id").execute()["id"]


# ── Internal helpers ───────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _col_letter(zero_index: int) -> str:
    """Convert 0-based column index to A1 letter notation."""
    letters = ""
    n = zero_index
    while True:
        letters = chr(65 + n % 26) + letters
        n = n // 26 - 1
        if n < 0:
            break
    return letters


def _append(sheet_id: str, tab: str, values: list[list]) -> None:
    _sheets().spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{tab}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


def _get_all_rows(sheet_id: str, tab: str) -> list[list]:
    result = _sheets().spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{tab}!A1:ZZ",
    ).execute()
    return result.get("values", [])


def _touch(sheet_id: str) -> None:
    _sheets().spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Season Config!B4",
        valueInputOption="RAW",
        body={"values": [[_now()]]},
    ).execute()


def _increment_game_count(sheet_id: str) -> None:
    sheets = _sheets()
    result = sheets.spreadsheets().values().get(
        spreadsheetId=sheet_id, range="Season Config!B5"
    ).execute()
    current = int((result.get("values") or [["0"]])[0][0])
    sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Season Config!B5",
        valueInputOption="RAW",
        body={"values": [[str(current + 1)]]},
    ).execute()


def _get_sheet_tab_id(sheet_id: str, tab_title: str) -> int:
    meta = _sheets().spreadsheets().get(spreadsheetId=sheet_id).execute()
    for s in meta["sheets"]:
        if s["properties"]["title"] == tab_title:
            return s["properties"]["sheetId"]
    raise ValueError(f"Tab '{tab_title}' not found in spreadsheet {sheet_id}")


# ── Match Log ──────────────────────────────────────────────────────────────

def append_match_log(sheet_id: str, row: dict) -> None:
    _append(sheet_id, "Match Log", [[
        row.get("draft_id", ""),
        row.get("game_number", ""),
        row.get("submitted_at", ""),
        row.get("blue_captain", ""),
        row.get("red_captain", ""),
        row.get("blue_picks", ""),
        row.get("red_picks", ""),
        row.get("blue_bans", ""),
        row.get("red_bans", ""),
        row.get("fearless_pool", ""),
        row.get("game_status", ""),
        row.get("winner", "TBD"),
        row.get("series_score", "TBD"),
    ]])
    _touch(sheet_id)


def update_match_result(sheet_id: str, draft_id: str, winner: str, series_score: str) -> bool:
    """Update Winner and Series Score for all Match Log rows with this draft_id."""
    sheets = _sheets()
    rows = _get_all_rows(sheet_id, "Match Log")
    if not rows:
        return False

    headers = rows[0]
    try:
        uid_col    = headers.index("Draft ID")
        winner_col = headers.index("Winner")
        score_col  = headers.index("Series Score")
    except ValueError:
        return False

    updated = False
    for i, row in enumerate(rows[1:], start=2):  # sheet rows are 1-indexed; row 1 is header
        if len(row) > uid_col and row[uid_col] == draft_id:
            sheets.spreadsheets().values().batchUpdate(
                spreadsheetId=sheet_id,
                body={"valueInputOption": "RAW", "data": [
                    {"range": f"Match Log!{_col_letter(winner_col)}{i}", "values": [[winner]]},
                    {"range": f"Match Log!{_col_letter(score_col)}{i}",  "values": [[series_score]]},
                ]},
            ).execute()
            updated = True

    if updated:
        _touch(sheet_id)
    return updated


# ── Player Stats ───────────────────────────────────────────────────────────

def append_player_stats(sheet_id: str, rows: list[dict]) -> None:
    values = [[
        r.get("draft_id", ""),
        r.get("game_number", ""),
        r.get("date", ""),
        r.get("player_name", ""),
        r.get("god", ""),
        r.get("role", ""),
        r.get("team", ""),
        r.get("k", ""), r.get("d", ""), r.get("a", ""),
        r.get("gpm", ""),
        r.get("player_damage", ""),
        r.get("minion_damage", ""),
        r.get("jungle_damage", ""),
        r.get("structure_damage", ""),
        r.get("damage_taken", ""),
        r.get("damage_mitigated", ""),
        r.get("self_healing", ""),
        r.get("ally_healing", ""),
        r.get("wards_placed", ""),
        r.get("win", ""),
    ] for r in rows]
    _append(sheet_id, "Player Stats", values)
    _touch(sheet_id)
    _increment_game_count(sheet_id)


# ── Unlinked ───────────────────────────────────────────────────────────────

def append_unlinked(sheet_id: str, row: dict) -> None:
    _append(sheet_id, "Unlinked", [[
        row.get("timestamp", ""),
        row.get("message_id", ""),
        row.get("parsed_player_names", ""),
        row.get("raw_stats_json", ""),
        row.get("notes", ""),
    ]])


def get_unlinked_rows(sheet_id: str) -> list[dict]:
    rows = _get_all_rows(sheet_id, "Unlinked")
    if len(rows) < 2:
        return []
    headers = rows[0]
    return [dict(zip(headers, row)) for row in rows[1:]]


def remove_unlinked_by_message_id(sheet_id: str, message_id: str) -> dict | None:
    """Find, remove, and return the Unlinked row for message_id. Returns None if not found."""
    sheets = _sheets()
    rows = _get_all_rows(sheet_id, "Unlinked")
    if len(rows) < 2:
        return None

    headers = rows[0]
    try:
        mid_col = headers.index("Discord Message ID")
    except ValueError:
        return None

    for i, row in enumerate(rows[1:], start=1):
        if len(row) > mid_col and row[mid_col] == message_id:
            matched = dict(zip(headers, row))
            tab_id = _get_sheet_tab_id(sheet_id, "Unlinked")
            sheets.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={"requests": [{"deleteDimension": {"range": {
                    "sheetId":    tab_id,
                    "dimension":  "ROWS",
                    "startIndex": i,        # 0-indexed; 0 = header, 1 = first data row
                    "endIndex":   i + 1,
                }}}]},
            ).execute()
            return matched

    return None


# ── Status query ───────────────────────────────────────────────────────────

def get_match_status(sheet_id: str, draft_id: str) -> dict:
    match_rows = _get_all_rows(sheet_id, "Match Log")
    stats_rows = _get_all_rows(sheet_id, "Player Stats")

    def filter_uid(rows, col_name):
        if not rows:
            return []
        headers = rows[0]
        if col_name not in headers:
            return []
        col = headers.index(col_name)
        return [r for r in rows[1:] if len(r) > col and r[col] == draft_id]

    matched_logs  = filter_uid(match_rows, "Draft ID")
    matched_stats = filter_uid(stats_rows, "Draft ID")

    result: dict = {
        "draft_id":         draft_id,
        "games":            [],
        "winner":           "TBD",
        "series_score":     "TBD",
        "stats_rows_found": len(matched_stats),
    }

    if match_rows and matched_logs:
        headers = match_rows[0]

        def col(name):
            return headers.index(name) if name in headers else None

        game_col   = col("Game Number")
        status_col = col("Game Status")
        winner_col = col("Winner")
        score_col  = col("Series Score")

        for row in matched_logs:
            result["games"].append({
                "game_number": row[game_col]   if game_col   is not None and len(row) > game_col   else "",
                "game_status": row[status_col] if status_col is not None and len(row) > status_col else "",
            })

        last = matched_logs[-1]
        if winner_col is not None and len(last) > winner_col:
            result["winner"] = last[winner_col]
        if score_col is not None and len(last) > score_col:
            result["series_score"] = last[score_col]

    return result


# ── Season Config ──────────────────────────────────────────────────────────

def get_season_config(sheet_id: str) -> dict:
    rows = _get_all_rows(sheet_id, "Season Config")
    return {row[0]: row[1] for row in rows[1:] if len(row) >= 2}
