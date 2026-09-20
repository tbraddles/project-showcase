"""Turn 2026 prediction CSVs into the compact JSON the night app loads."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "data" / "night.json"
VOTES_CSV = ROOT / "output" / "2026" / "brownlow_2026_heatmap_votes.csv"
GAMES_CSV = ROOT / "output" / "2026" / "brownlow_2026_player_game_probabilities.csv"

TEAM_META = {
    "AD": {"name": "Adelaide", "short": "Crows", "color": "#002b5c", "accent": "#e3b505"},
    "BL": {"name": "Brisbane", "short": "Lions", "color": "#a30046", "accent": "#fdb714"},
    "CA": {"name": "Carlton", "short": "Blues", "color": "#0e1e5b", "accent": "#ffffff"},
    "CW": {"name": "Collingwood", "short": "Pies", "color": "#111111", "accent": "#ffffff"},
    "ES": {"name": "Essendon", "short": "Bombers", "color": "#cc2031", "accent": "#111111"},
    "FR": {"name": "Fremantle", "short": "Dockers", "color": "#2a0a45", "accent": "#ffffff"},
    "GE": {"name": "Geelong", "short": "Cats", "color": "#1c3c63", "accent": "#ffffff"},
    "GC": {"name": "Gold Coast", "short": "Suns", "color": "#e21e26", "accent": "#f5c518"},
    "GW": {"name": "GWS", "short": "Giants", "color": "#f47920", "accent": "#000000"},
    "HW": {"name": "Hawthorn", "short": "Hawks", "color": "#4d2004", "accent": "#fbbf24"},
    "ME": {"name": "Melbourne", "short": "Demons", "color": "#0b3c2f", "accent": "#cc2031"},
    "NM": {"name": "North Melbourne", "short": "Kangaroos", "color": "#013b7b", "accent": "#ffffff"},
    "PA": {"name": "Port Adelaide", "short": "Power", "color": "#008aab", "accent": "#111111"},
    "RI": {"name": "Richmond", "short": "Tigers", "color": "#111111", "accent": "#ffd200"},
    "SK": {"name": "St Kilda", "short": "Saints", "color": "#ed1b2f", "accent": "#ffffff"},
    "SY": {"name": "Sydney", "short": "Swans", "color": "#ed171f", "accent": "#ffffff"},
    "WC": {"name": "West Coast", "short": "Eagles", "color": "#003087", "accent": "#f4c542"},
    "WB": {"name": "Western Bulldogs", "short": "Bulldogs", "color": "#014896", "accent": "#d51920"},
}


def pretty_name(name: str) -> str:
    bits = []
    for part in str(name).replace("-", " ").split():
        word = part.capitalize()
        lower = word.lower()
        if lower.startswith("mc") and len(word) > 2:
            word = "Mc" + word[2:].capitalize()
        if lower.startswith("mac") and len(word) > 3:
            word = "Mac" + word[3:].capitalize()
        bits.append(word)
    pretty = " ".join(bits)
    original = str(name)
    if "-" in original:
        # Restore hyphens between the split tokens in order.
        tokens = original.replace("-", " ").split()
        rebuilt = pretty.split()
        out = []
        src = original.upper()
        i = 0
        for raw in original.split():
            chunk = raw.split("-")
            joined = "-".join(rebuilt[i : i + len(chunk)])
            out.append(joined)
            i += len(chunk)
        return " ".join(out)
    return pretty


def round_label(round_no: int) -> str:
    number = int(round_no)
    return "Opening" if number == 1 else f"R{number - 1}"


def certainty_from_scores(scores: np.ndarray) -> dict:
    """
    Badge + conviction on the same scale.

    The number is 8-97 'how separated is this 3-2-1'.
    LOCK lives 72-97, LEAN 50-71, TOSS-UP 8-49, so a lean can never
    outrank a lock on the ticket.
    """
    ranked = np.sort(scores)[::-1]
    bog_edge = float(ranked[0] - ranked[1]) if len(ranked) > 1 else 1.0
    cut_edge = float(ranked[2] - ranked[3]) if len(ranked) > 3 else float(ranked[-1])
    span = float(ranked[0] - ranked[3]) if len(ranked) > 3 else float(ranked[0] - ranked[-1])
    strength = (
        0.40 * min(span / 0.70, 1.0)
        + 0.35 * min(bog_edge / 0.40, 1.0)
        + 0.25 * min(cut_edge / 0.25, 1.0)
    )
    raw = int(round(8 + 89 * min(max(strength, 0.0), 1.0)))

    if bog_edge >= 0.22 and cut_edge >= 0.09:
        label = "LOCK"
        pct = max(raw, 72)
        blurb = (
            "Smash lock. Podium is well clear of 4th."
            if pct >= 88
            else "Lock, but not a blowout. 3-2-1 looks right; gaps aren't huge."
        )
    elif bog_edge >= 0.11 or span >= 0.40:
        label = "LEAN"
        pct = min(max(raw, 50), 71)
        blurb = "Lean, not a lock. Model likes this 3-2-1 but 1st vs 2nd or 3rd vs 4th is close."
    else:
        label = "TOSS-UP"
        pct = min(raw, 49)
        blurb = "Toss-up. Tight card — don't die in a hole here."
    return {
        "label": label,
        "pct": pct,
        "bogEdge": round(bog_edge, 3),
        "cutEdge": round(cut_edge, 3),
        "blurb": blurb,
    }


def main() -> None:
    votes = pd.read_csv(VOTES_CSV)
    games_raw = pd.read_csv(GAMES_CSV)

    round_cols = [c for c in votes.columns if c.startswith("round_")]
    leaderboard = []
    for rank, (_, row) in enumerate(votes.iterrows(), start=1):
        threes = int((row[round_cols] == 3).sum())
        twos = int((row[round_cols] == 2).sum())
        ones = int((row[round_cols] == 1).sum())
        leaderboard.append(
            {
                "rank": rank,
                "player": pretty_name(row["player"]),
                "team": row["team"],
                "votes": int(row["total_votes"]),
                "threes": threes,
                "twos": twos,
                "ones": ones,
            }
        )

    clubs = []
    for code, meta in TEAM_META.items():
        club_board = [p for p in leaderboard if p["team"] == code][:6]
        if not club_board:
            continue
        clubs.append(
            {
                "team": code,
                **meta,
                "leader": club_board[0]["player"],
                "leaderVotes": club_board[0]["votes"],
                "board": club_board,
            }
        )
    clubs.sort(key=lambda c: (-c["leaderVotes"], c["name"]))

    games = []
    labels = []
    grouped = games_raw.sort_values(["date", "game_id", "vote_probability"], ascending=[True, True, False])
    for game_id, frame in grouped.groupby("game_id", sort=False):
        frame = frame.sort_values("vote_probability", ascending=False).reset_index(drop=True)
        head = frame.iloc[0]
        scores = frame["vote_probability"].to_numpy(dtype=float)
        cert = certainty_from_scores(scores)
        labels.append(cert["label"])
        podium = []
        for i, rec in frame.head(6).iterrows():
            votes_321 = {0: 3, 1: 2, 2: 1}.get(int(i), 0)
            podium.append(
                {
                    "player": pretty_name(rec["player"]),
                    "team": rec["team"],
                    "votes": votes_321,
                    "score": round(float(rec["vote_probability"]), 3),
                    "disp": int(rec["disp"]) if pd.notna(rec["disp"]) else 0,
                    "goals": int(rec["goals"]) if pd.notna(rec["goals"]) else 0,
                    "tackles": int(rec["tackles"]) if pd.notna(rec["tackles"]) else 0,
                    "clearances": int(rec["clearances"]) if pd.notna(rec["clearances"]) else 0,
                }
            )
        games.append(
            {
                "id": int(game_id),
                "round": int(head["round"]),
                "label": round_label(head["round"]),
                "date": str(head["date"]),
                "day": str(head["day"]),
                "venue": str(head["venue"]),
                "home": {
                    "code": head["home_team_code"],
                    "name": TEAM_META.get(head["home_team_code"], {}).get("name", head["home_team"].title()),
                    "score": int(head["home_total"]),
                },
                "away": {
                    "code": head["away_team_code"],
                    "name": TEAM_META.get(head["away_team_code"], {}).get("name", head["away_team"].title()),
                    "score": int(head["away_total"]),
                },
                "certainty": cert,
                "podium": podium[:3],
                "next": podium[3:],
            }
        )

    rounds = []
    for round_no, pack in pd.DataFrame(games).groupby("round", sort=True):
        rounds.append(
            {
                "round": int(round_no),
                "label": round_label(round_no),
                "count": int(len(pack)),
            }
        )

    payload = {
        "season": 2026,
        "title": "Sizzle Card",
        "gamesCount": len(games),
        "leaderboard": leaderboard,
        "clubs": clubs,
        "rounds": rounds,
        "games": games,
        "teams": TEAM_META,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    from collections import Counter

    print(f"Wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
    print("Games", len(games), "players", len(leaderboard))
    print("Certainty mix", dict(Counter(labels)))


if __name__ == "__main__":
    main()
