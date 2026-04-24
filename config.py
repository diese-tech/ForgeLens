import json
import os
import tempfile

from dotenv import load_dotenv

load_dotenv()

# ── Railway / hosted environment: credentials JSON stored as env var ───────
# On Railway, you can't upload files directly. Instead, paste the entire
# contents of your credentials JSON file into a Railway env var called
# GOOGLE_CREDENTIALS_JSON. This block writes it to a temp file at startup.
_creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if _creds_json:
    _tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(json.loads(_creds_json), _tmp)
    _tmp.close()
    os.environ["GOOGLE_CREDENTIALS_PATH"] = _tmp.name

# ── League identity ────────────────────────────────────────────────────────
LEAGUE_NAME = "Frank's Retirement Home"
LEAGUE_SLUG = "franks-retirement-home"
LEAGUE_PREFIX = os.getenv("LEAGUE_PREFIX", "FRH")  # used by /newmatch for non-GodForge servers

# ── Discord ────────────────────────────────────────────────────────────────
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SCREENSHOT_CHANNEL_ID = int(os.getenv("SCREENSHOT_CHANNEL_ID"))
JSON_CHANNEL_ID = int(os.getenv("JSON_CHANNEL_ID"))
ADMIN_REPORT_CHANNEL_ID = int(os.getenv("ADMIN_REPORT_CHANNEL_ID"))
STAFF_ROLE_IDS = [int(rid.strip()) for rid in os.getenv("STAFF_ROLE_IDS", "").split(",") if rid.strip()]

# ── Google ─────────────────────────────────────────────────────────────────
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "franks-retirement-home-credentials.json")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PARENT_DRIVE_FOLDER_ID = os.getenv("PARENT_DRIVE_FOLDER_ID") or None
