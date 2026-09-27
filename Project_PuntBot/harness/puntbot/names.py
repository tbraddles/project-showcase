"""Normalize horse and venue names so form and Betfair rows can be joined."""

from __future__ import annotations

import re
import unicodedata

_COUNTRY_SUFFIX = re.compile(
    r"""
    (?:
        \s+\((?:nz|aus|usa|fr|uk|ire|sa|can)\)
        |
        \s+(?:nz|aus|usa)
    )
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)
_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")
_VENUE_NOISE = re.compile(
    r"\b(park|paceway|trots|trotters|harness|racing|tabcorp)\b",
    re.IGNORECASE,
)


def normalize_horse_name(name: str | None) -> str:
    """Lowercase, strip country suffixes, and drop punctuation."""
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("'", "").replace("`", "").replace("’", "")
    text = _COUNTRY_SUFFIX.sub("", text)
    text = text.lower()
    text = _NON_ALNUM.sub(" ", text)
    text = _WS.sub(" ", text).strip()
    return text


def normalize_venue_name(name: str | None) -> str:
    """Collapse venue spelling so 'Tabcorp Park Melton' matches 'Melton'."""
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = _VENUE_NOISE.sub(" ", text)
    text = _NON_ALNUM.sub(" ", text)
    text = _WS.sub(" ", text).strip()
    return text
