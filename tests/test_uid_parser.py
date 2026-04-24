import pytest
from utils.uid_parser import extract_uid


# ── GodForge UIDs (GF- prefix) ────────────────────────────────────────────

def test_godforge_uid_plain():
    assert extract_uid("GF-08R8") == "GF-08R8"

def test_godforge_uid_in_sentence():
    assert extract_uid("Here are my screenshots for GF-FB6D, thanks") == "GF-FB6D"

def test_godforge_uid_in_filename():
    assert extract_uid(filenames=["Franks-Retirement-Home_bot-talk_GF-08R8.json"]) == "GF-08R8"


# ── League-prefix UIDs (/newmatch style) ──────────────────────────────────

def test_frh_prefix():
    assert extract_uid("FRH-A1B2") == "FRH-A1B2"

def test_three_letter_prefix():
    assert extract_uid("OWL-1234") == "OWL-1234"

def test_four_letter_prefix():
    assert extract_uid("SMTE-AB12") == "SMTE-AB12"

def test_uid_in_match_announcement():
    assert extract_uid("Match ID: FRH-X9Y2 — include this in your screenshot") == "FRH-X9Y2"


# ── Pattern boundaries ────────────────────────────────────────────────────

def test_uid_all_digits_suffix():
    assert extract_uid("GF-1234") == "GF-1234"

def test_uid_all_letters_suffix():
    assert extract_uid("GF-ABCD") == "GF-ABCD"

def test_uid_mixed_suffix():
    assert extract_uid("GF-A1B2") == "GF-A1B2"

def test_lowercase_prefix_not_matched():
    assert extract_uid("gf-08r8") is None

def test_lowercase_suffix_not_matched():
    assert extract_uid("GF-08r8") is None

def test_too_short_suffix_not_matched():
    assert extract_uid("GF-08R") is None

def test_five_char_suffix_not_matched():
    # Word boundary means GF-08R8X won't match GF-08R8 since it's mid-word
    assert extract_uid("GF-08R8X") is None

def test_single_letter_prefix_not_matched():
    assert extract_uid("G-08R8") is None

def test_five_letter_prefix_not_matched():
    assert extract_uid("SMITE-08R8") is None


# ── Multiple UIDs — first wins ────────────────────────────────────────────

def test_returns_first_uid():
    assert extract_uid("GF-08R8 and GF-FB6D") == "GF-08R8"

def test_text_uid_before_filename_uid():
    assert extract_uid("FRH-AAAA", filenames=["GF-BBBB.json"]) == "FRH-AAAA"

def test_falls_back_to_filename():
    assert extract_uid("", filenames=["league_FRH-CCCC.json"]) == "FRH-CCCC"


# ── Edge cases ────────────────────────────────────────────────────────────

def test_no_uid_in_text():
    assert extract_uid("no draft id here") is None

def test_empty_text():
    assert extract_uid("") is None

def test_no_arguments():
    assert extract_uid() is None

def test_filenames_none():
    assert extract_uid("GF-08R8", filenames=None) == "GF-08R8"

def test_no_uid_in_filename():
    assert extract_uid(filenames=["random-file.json"]) is None
