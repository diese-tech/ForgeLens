"""
Merges Scoreboard extraction (role data) with Details extraction (stat data)
for the same player within a single message submission.

Both screenshot types arrive in the same message. This module pairs them by
matching player names across the two extractions, then produces unified rows
ready for Player Stats.
"""

import difflib


def merge_extractions(scoreboard: dict, details: dict, draft_id: str, game_number, date: str) -> list[dict]:
    """
    Combine scoreboard and details Gemini results into Player Stats rows.

    If only one extraction type is available, the merge still produces rows —
    missing fields are left as empty strings.
    """
    order_stats  = details.get("order_players", []) if details else []
    chaos_stats  = details.get("chaos_players", []) if details else []
    order_scores = scoreboard.get("order_players", []) if scoreboard else []
    chaos_scores = scoreboard.get("chaos_players", []) if scoreboard else []

    rows = []
    rows += _merge_team(order_stats, order_scores, team="Order", draft_id=draft_id,
                        game_number=game_number, date=date)
    rows += _merge_team(chaos_stats, chaos_scores, team="Chaos", draft_id=draft_id,
                        game_number=game_number, date=date)
    return rows


def _merge_team(
    stats_players: list[dict],
    score_players: list[dict],
    team: str,
    draft_id: str,
    game_number,
    date: str,
) -> list[dict]:
    rows = []
    score_by_name = {p.get("player_name", "").lower(): p for p in score_players}

    for player in stats_players:
        name = player.get("player_name", "")
        score = _best_match(name.lower(), score_by_name)

        rows.append({
            "draft_id":         draft_id,
            "game_number":      game_number,
            "date":             date,
            "player_name":      name,
            "god":              score.get("god", ""),
            "role":             score.get("role", ""),
            "team":             team,
            "k":                player.get("k", ""),
            "d":                player.get("d", ""),
            "a":                player.get("a", ""),
            "gpm":              player.get("gpm", ""),
            "player_damage":    player.get("player_damage", ""),
            "minion_damage":    player.get("minion_damage", ""),
            "jungle_damage":    player.get("jungle_damage", ""),
            "structure_damage": player.get("structure_damage", ""),
            "damage_taken":     player.get("damage_taken", ""),
            "damage_mitigated": player.get("damage_mitigated", ""),
            "self_healing":     player.get("self_healing", ""),
            "ally_healing":     player.get("ally_healing", ""),
            "wards_placed":     player.get("wards_placed", ""),
            "win":              "",  # set later by /result or best-effort parse
        })

    # Players in scoreboard but not in details (e.g. details page only partially extracted)
    matched_names = {p.get("player_name", "").lower() for p in stats_players}
    for name_key, score in score_by_name.items():
        if name_key not in matched_names:
            rows.append({
                "draft_id":    draft_id,
                "game_number": game_number,
                "date":        date,
                "player_name": score.get("player_name", ""),
                "god":         score.get("god", ""),
                "role":        score.get("role", ""),
                "team":        team,
                **{k: "" for k in [
                    "k","d","a","gpm","player_damage","minion_damage","jungle_damage",
                    "structure_damage","damage_taken","damage_mitigated",
                    "self_healing","ally_healing","wards_placed","win",
                ]},
            })

    return rows


def _best_match(name_lower: str, score_by_name: dict) -> dict:
    """Return the scoreboard entry whose name best matches, or {} if no close match."""
    if name_lower in score_by_name:
        return score_by_name[name_lower]
    matches = difflib.get_close_matches(name_lower, score_by_name.keys(), n=1, cutoff=0.7)
    return score_by_name[matches[0]] if matches else {}
