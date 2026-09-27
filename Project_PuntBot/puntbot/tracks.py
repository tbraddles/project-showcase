"""Meeting-code to Betfair venue mapping."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

import config
from puntbot.names import normalize_venue_name


# Older / alternate HRA meeting codes that should join as the modern code.
CODE_ALIASES = {
    "ME": "MX",
    "MB": "PC",
}


@lru_cache(maxsize=1)
def load_track_rows(path: Path | None = None) -> list[dict[str, str]]:
    csv_path = path or config.TRACK_CODES_PATH
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def code_to_betfair_name() -> dict[str, str]:
    mapping = {row["code"].upper(): row["betfair_name"] for row in load_track_rows()}
    for alias, primary in CODE_ALIASES.items():
        if primary in mapping:
            mapping[alias] = mapping[primary]
    return mapping


@lru_cache(maxsize=1)
def venue_lookup() -> dict[str, str]:
    """Map a normalized venue string (code, official name, or alias) to a code."""
    lookup: dict[str, str] = {}
    for row in load_track_rows():
        code = row["code"].upper()
        lookup[normalize_venue_name(code)] = code
        lookup[normalize_venue_name(row["betfair_name"])] = code
        aliases = row.get("aliases") or ""
        for alias in aliases.split("|"):
            alias = alias.strip()
            if alias:
                lookup[normalize_venue_name(alias)] = code
    return lookup


def canonical_code(track: str | None) -> str | None:
    if not track:
        return None
    raw = str(track).strip()
    if len(raw) <= 3 and raw.isalpha():
        code = raw.upper()
        return CODE_ALIASES.get(code, code)
    return venue_lookup().get(normalize_venue_name(raw))


def canonical_venue(track: str | None) -> str | None:
    code = canonical_code(track)
    if not code:
        return None
    return code_to_betfair_name().get(code)


def display_venue(track: str | None) -> str:
    return canonical_venue(track) or (track or "").strip()
