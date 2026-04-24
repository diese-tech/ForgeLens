import re

# Matches any 2-4 uppercase letter prefix followed by a hyphen and 4 alphanumeric characters.
# Covers GodForge UIDs (GF-XXXX) and /newmatch UIDs (FRH-XXXX, OWL-XXXX, etc.).
# Uses lookarounds instead of \b because \b treats _ as a word character,
# which breaks matching inside GodForge filenames like _GF-08R8.json.
_UID_PATTERN = re.compile(r"(?<![A-Z0-9])[A-Z]{2,4}-[A-Z0-9]{4}(?![A-Z0-9])")


def extract_uid(text: str = "", filenames: list[str] = None) -> str | None:
    """Return the first draft_id found in text or filenames, or None."""
    for source in [text] + (filenames or []):
        match = _UID_PATTERN.search(source)
        if match:
            return match.group()
    return None
