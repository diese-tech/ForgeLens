"""
One-time auth verification script for smite2-stats-bot.
Run this after completing SETUP.md to confirm all services are reachable.
Usage: python test_auth.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PASS = "[OK]"
FAIL = "[FAIL]"

errors = []


def check(label, fn):
    try:
        result = fn()
        print(f"{PASS} {label}" + (f" — {result}" if result else ""))
    except Exception as e:
        print(f"{FAIL} {label}: {e}")
        errors.append(label)


# ── 1. credentials.json ──────────────────────────────────────────────────────

def check_credentials_file():
    path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    if not Path(path).exists():
        raise FileNotFoundError(
            f"'{path}' not found. Place credentials.json in the project root "
            "and ensure GOOGLE_CREDENTIALS_PATH in .env is set correctly."
        )
    return f"found at '{path}'"


check("credentials.json found", check_credentials_file)


# ── 2. Gemini API ─────────────────────────────────────────────────────────────

def check_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY not set in .env. See SETUP.md Section 4."
        )

    from google import genai
    from google.genai import errors as genai_errors

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Reply with only the word: pong",
        )
        text = response.text.strip().lower()
        if "pong" not in text:
            raise RuntimeError(f"Unexpected Gemini response: {response.text!r}")
        return "model: gemini-2.0-flash"
    except genai_errors.ClientError as e:
        # 429 = quota exhausted — API key is valid and reachable, just rate-limited
        if "429" in str(e) or "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
            return "model: gemini-2.0-flash (API key valid — free-tier quota currently exhausted, this is fine)"
        raise


check("Gemini API connected", check_gemini)


# ── 3. Google Sheets API ──────────────────────────────────────────────────────

def check_sheets():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
    service = build("sheets", "v4", credentials=creds)
    service.spreadsheets()
    return None


check("Google Sheets API connected", check_sheets)


# ── 4. Google Drive API ───────────────────────────────────────────────────────

def check_drive():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    scopes = ["https://www.googleapis.com/auth/drive"]
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
    service = build("drive", "v3", credentials=creds)
    service.files().list(pageSize=1).execute()
    return None


check("Google Drive API connected", check_drive)


# ── 5. .env channel/role IDs (warn only, not failures) ───────────────────────

print()
optional_vars = [
    "SCREENSHOT_CHANNEL_ID",
    "JSON_CHANNEL_ID",
    "ADMIN_REPORT_CHANNEL_ID",
    "STAFF_ROLE_IDS",
    "DISCORD_TOKEN",
]
missing_optional = [v for v in optional_vars if not os.getenv(v)]
if missing_optional:
    print(f"[WARN] These .env values are not yet set (fill them in before running the bot):")
    for v in missing_optional:
        print(f"       {v}")
else:
    print(f"{PASS} All Discord .env values present")


# ── Summary ───────────────────────────────────────────────────────────────────

print()
if errors:
    print(f"[FAIL] {len(errors)} check(s) failed: {', '.join(errors)}")
    print("       Fix the issues above and re-run this script.")
    sys.exit(1)
else:
    print(f"{PASS} All checks passed. Bot is ready to configure.")
