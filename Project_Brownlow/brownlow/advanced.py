"""Fetch and join Champion-style advanced stats (Fryzigg dump + AFL.com.au)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

import config

ADVANCED_KEEP_COLS = [
    "year",
    "round",
    "date",
    "player_first_name",
    "player_last_name",
    "player_team",
    "player_position",
    *config.ADVANCED_STAT_COLS,
]

_AFL_HEADERS = {"User-Agent": "Project-Brownlow/1.0"}
_MELBOURNE = ZoneInfo("Australia/Melbourne")


def normalize_person_name(name: str) -> str:
    """Uppercase a person name and strip punctuation so O'Sullivan matches OSULLIVAN."""
    text = str(name).upper()
    for char in ("'", "'", "'", "`", "-", ".", ",", "’"):
        text = text.replace(char, "")
    return " ".join(text.split())


def team_code_from_name(name: str | None) -> str | None:
    """Map AFL Tables / Fryzigg / AFL.com.au team names to two-letter codes."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return None
    raw = str(name).strip()
    if raw in config.TEAM_CODE_MAP:
        return config.TEAM_CODE_MAP[raw]
    key = " ".join(raw.lower().split())
    if key in config.TEAM_CODE_ALIASES:
        return config.TEAM_CODE_ALIASES[key]
    for full, code in config.TEAM_CODE_MAP.items():
        if full.lower() == key:
            return code
    return None


def parse_advanced_round(value) -> int | None:
    """Keep numbered home-and-away rounds; Opening Round becomes 0; finals are dropped."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d+", text):
        return int(text)
    if text.casefold() in {"opening round", "or"}:
        return 0
    return None


def _melbourne_date(utc_start: str) -> str:
    stamp = utc_start[:19]
    utc = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return utc.astimezone(_MELBOURNE).date().isoformat()


def download_fryzigg_rds(
    cache_path: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Download the Fryzigg player-stats RDS once and cache it under data/raw."""
    path = Path(cache_path) if cache_path is not None else config.FRYZIGG_CACHE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        print(f"Using cached Fryzigg dump at {path}")
        return path

    print(f"Downloading Fryzigg dump from {config.FRYZIGG_RDS_URL}")
    response = requests.get(config.FRYZIGG_RDS_URL, timeout=120, stream=True)
    response.raise_for_status()
    with path.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)
    print(f"Saved Fryzigg dump to {path}")
    return path


def load_fryzigg_frame(cache_path: str | Path | None = None) -> pd.DataFrame:
    """Read the cached RDS into a DataFrame."""
    import pyreadr

    path = Path(cache_path) if cache_path is not None else config.FRYZIGG_CACHE_PATH
    result = pyreadr.read_r(str(path))
    return list(result.values())[0]


def fryzigg_year_frame(raw: pd.DataFrame, year: int) -> pd.DataFrame:
    """Slice one season from the Fryzigg dump into the shared advanced-stat schema."""
    frame = raw.copy()
    frame["date"] = pd.to_datetime(frame["match_date"], errors="coerce")
    season = frame[frame["date"].dt.year == year].copy()
    if season.empty:
        return season

    season["year"] = year
    season["round"] = season["match_round"].map(parse_advanced_round)
    season["date"] = season["date"].dt.strftime("%Y-%m-%d")
    rename = {
        "tackles_inside_fifty": "tackles_inside_fifty",
        "disposal_efficiency_percentage": "disposal_efficiency_percentage",
        "effective_disposals": "effective_disposals",
        "score_involvements": "score_involvements",
        "metres_gained": "metres_gained",
        "intercepts": "intercepts",
        "pressure_acts": "pressure_acts",
        "turnovers": "turnovers",
        "centre_clearances": "centre_clearances",
        "ground_ball_gets": "ground_ball_gets",
        "player_first_name": "player_first_name",
        "player_last_name": "player_last_name",
        "player_team": "player_team",
        "player_position": "player_position",
    }
    available = [col for col in rename if col in season.columns]
    out = season[["year", "round", "date", *available]].copy()
    return out.reindex(columns=ADVANCED_KEEP_COLS)


def _afl_comp_id(session: requests.Session) -> int:
    response = session.get(
        "https://aflapi.afl.com.au/afl/v2/competitions",
        params={"pageSize": 50},
        timeout=30,
    )
    response.raise_for_status()
    competitions = response.json().get("competitions") or []
    ids = [
        row["id"]
        for row in competitions
        if row.get("code") == "AFL" and "Legacy" not in str(row.get("name", ""))
    ]
    if not ids:
        raise RuntimeError("Could not find the AFL men's competition id")
    return min(ids)


def _afl_season_id(session: requests.Session, year: int, comp_id: int) -> int:
    response = session.get(
        f"https://aflapi.afl.com.au/afl/v2/competitions/{comp_id}/compseasons",
        params={"pageSize": 100},
        timeout=30,
    )
    response.raise_for_status()
    seasons = response.json().get("compSeasons") or []
    matches = [
        row["id"]
        for row in seasons
        if str(year) in str(row.get("name", "")) and "Legacy" not in str(row.get("name", ""))
    ]
    if not matches:
        raise RuntimeError(f"Could not find AFL.com.au season id for {year}")
    return matches[0]


def _afl_token(session: requests.Session) -> str:
    response = session.post("https://api.afl.com.au/cfs/afl/WMCTok", timeout=30)
    response.raise_for_status()
    token = response.json().get("token")
    if not token:
        raise RuntimeError("AFL.com.au did not return an API token")
    return token


def _afl_player_identity(entry: dict) -> tuple[str, str, str]:
    given = surname = ""
    position = ""
    node = entry.get("player") or {}
    for _ in range(5):
        if not isinstance(node, dict):
            break
        if node.get("position"):
            position = str(node["position"])
        name = node.get("playerName")
        if isinstance(name, dict):
            given = name.get("givenName") or given
            surname = name.get("surname") or surname
        node = node.get("player") or {}
    return str(given), str(surname), position


def _flatten_afl_player(entry: dict, team_name: str, match_date: str, year: int, round_number) -> dict:
    given, surname, position = _afl_player_identity(entry)
    stats = ((entry.get("playerStats") or {}).get("stats")) or {}
    extended = stats.get("extendedStats") or {}
    clearances = stats.get("clearances") or {}
    return {
        "year": year,
        "round": round_number,
        "date": match_date,
        "player_first_name": given,
        "player_last_name": surname,
        "player_team": team_name,
        "player_position": position,
        "score_involvements": stats.get("scoreInvolvements"),
        "metres_gained": stats.get("metresGained"),
        "intercepts": stats.get("intercepts"),
        "turnovers": stats.get("turnovers"),
        "centre_clearances": clearances.get("centreClearances"),
        "tackles_inside_fifty": stats.get("tacklesInside50"),
        "disposal_efficiency_percentage": stats.get("disposalEfficiency"),
        "pressure_acts": extended.get("pressureActs"),
        "ground_ball_gets": extended.get("groundBallGets"),
        "effective_disposals": extended.get("effectiveDisposals"),
    }


def fetch_afl_advanced_year(year: int) -> pd.DataFrame:
    """Pull concluded-match advanced stats for one season from AFL.com.au."""
    session = requests.Session()
    session.headers.update(_AFL_HEADERS)
    comp_id = _afl_comp_id(session)
    season_id = _afl_season_id(session, year, comp_id)
    fixture = session.get(
        "https://aflapi.afl.com.au/afl/v2/matches",
        params={"competitionId": comp_id, "compSeasonId": season_id, "pageSize": 1000},
        timeout=60,
    )
    fixture.raise_for_status()
    matches = fixture.json().get("matches") or []
    concluded = [row for row in matches if str(row.get("status", "")).upper() == "CONCLUDED"]
    print(f"AFL.com.au {year}: {len(concluded)} concluded matches")
    token = _afl_token(session)

    rows: list[dict] = []
    for index, match in enumerate(concluded, start=1):
        provider_id = match.get("providerId")
        if not provider_id:
            continue
        stats_resp = session.get(
            f"https://api.afl.com.au/cfs/afl/playerStats/match/{provider_id}",
            headers={"x-media-mis-token": token},
            timeout=30,
        )
        if not stats_resp.ok:
            print(f"  skip {provider_id} ({stats_resp.status_code})")
            continue
        payload = stats_resp.json()
        match_date = _melbourne_date(match["utcStartTime"])
        round_raw = (match.get("round") or {}).get("roundNumber")
        round_number = parse_advanced_round(round_raw)
        home_name = ((match.get("home") or {}).get("team") or {}).get("name")
        away_name = ((match.get("away") or {}).get("team") or {}).get("name")
        for entry in payload.get("homeTeamPlayerStats") or []:
            rows.append(_flatten_afl_player(entry, home_name, match_date, year, round_number))
        for entry in payload.get("awayTeamPlayerStats") or []:
            rows.append(_flatten_afl_player(entry, away_name, match_date, year, round_number))
        if index == 1 or index % 25 == 0 or index == len(concluded):
            print(f"  {index}/{len(concluded)} matches")

    if not rows:
        return pd.DataFrame(columns=ADVANCED_KEEP_COLS)
    return pd.DataFrame(rows).reindex(columns=ADVANCED_KEEP_COLS)


def write_advanced_year(frame: pd.DataFrame, year: int, raw_dir: Path) -> Path:
    path = raw_dir / f"{year}_AFL_Advanced_Stats.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    print(f"Wrote {len(frame)} advanced-stat rows to {path}")
    return path


def scrape_advanced_stats(
    years: list[int] | None = None,
    raw_dir: str | Path | None = None,
    force: bool = False,
) -> dict[int, Path]:
    """
    Write yearly advanced-stat CSVs under data/raw.

    Uses the Fryzigg RDS for seasons it covers, then AFL.com.au for any remaining
    years (currently needed for the live prediction season).
    """
    seasons = years if years is not None else list(config.PLAYER_YEARS)
    tables_dir = Path(raw_dir) if raw_dir is not None else config.DATA_RAW_DIR
    tables_dir.mkdir(parents=True, exist_ok=True)

    written: dict[int, Path] = {}
    fryzigg_years: set[int] = set()
    try:
        cache = download_fryzigg_rds(tables_dir / config.FRYZIGG_CACHE_PATH.name, force=force)
        dump = load_fryzigg_frame(cache)
        dump_dates = pd.to_datetime(dump["match_date"], errors="coerce")
        fryzigg_years = set(dump_dates.dt.year.dropna().astype(int))
        for year in seasons:
            if year not in fryzigg_years:
                continue
            year_frame = fryzigg_year_frame(dump, year)
            written[year] = write_advanced_year(year_frame, year, tables_dir)
    except Exception as exc:
        print(f"Fryzigg dump unavailable ({exc}); will try AFL.com.au for requested years.")

    missing = [year for year in seasons if year not in written]
    for year in missing:
        print(f"Fetching {year} advanced stats from AFL.com.au")
        year_frame = fetch_afl_advanced_year(year)
        if year_frame.empty:
            print(f"No AFL.com.au advanced stats for {year}")
            continue
        written[year] = write_advanced_year(year_frame, year, tables_dir)

    return written


def load_advanced_stats(
    raw_dir: str | Path | None = None,
    years: list[int] | None = None,
) -> pd.DataFrame:
    """Load yearly advanced CSVs; missing seasons are skipped with a note."""
    tables_dir = Path(raw_dir) if raw_dir is not None else config.DATA_RAW_DIR
    seasons = years if years is not None else list(config.PLAYER_YEARS)
    frames = []
    for year in seasons:
        path = tables_dir / f"{year}_AFL_Advanced_Stats.csv"
        if not path.exists():
            print(f"No advanced stats file for {year} ({path.name})")
            continue
        frames.append(pd.read_csv(path))
    if not frames:
        return pd.DataFrame(columns=ADVANCED_KEEP_COLS)
    return pd.concat(frames, ignore_index=True)


def _ensure_advanced_columns(players: pd.DataFrame) -> pd.DataFrame:
    out = players.copy()
    for col in config.ADVANCED_STAT_COLS:
        if col not in out.columns:
            out[col] = pd.NA
    if "player_position" not in out.columns:
        out["player_position"] = pd.NA
    if "is_midfielder" not in out.columns:
        out["is_midfielder"] = pd.NA
    return out


def _fill_from_suffix(merged: pd.DataFrame, stat_cols: list[str], suffix: str) -> pd.DataFrame:
    for col in stat_cols:
        extra = f"{col}{suffix}"
        if extra in merged.columns:
            merged[col] = merged[col].combine_first(merged[extra])
            merged = merged.drop(columns=[extra])
    return merged


def attach_advanced_stats(players: pd.DataFrame, advanced: pd.DataFrame) -> pd.DataFrame:
    """
    Left-join advanced stats onto player-games.

    Primary key is match date + team code + punctuation-stripped name. Unmatched
    rows fall back to a unique last-name within that team-game so Mitch/Mitchell
    still join when the surname is unambiguous.
    """
    players = _ensure_advanced_columns(players)
    if advanced is None or advanced.empty:
        return players

    adv = advanced.copy()
    adv["date"] = pd.to_datetime(adv["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    adv["team"] = adv["player_team"].map(team_code_from_name)
    adv["player_name"] = (
        adv["player_first_name"].fillna("").astype(str)
        + " "
        + adv["player_last_name"].fillna("").astype(str)
    ).map(normalize_person_name)
    adv["last_name"] = adv["player_last_name"].map(normalize_person_name)

    out = players.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["player_name"] = out["player"].map(normalize_person_name).replace(config.PLAYER_NAME_ALIASES)
    out["last_name"] = out["player_name"].str.split().str[-1]

    stat_cols = [*config.ADVANCED_STAT_COLS, "player_position"]
    adv_name = (
        adv.dropna(subset=["date", "team", "player_name"])
        .drop_duplicates(["date", "team", "player_name"], keep="first")
        [["date", "team", "player_name", *stat_cols]]
    )
    merged = _fill_from_suffix(
        out.merge(adv_name, on=["date", "team", "player_name"], how="left", suffixes=("", "_adv")),
        stat_cols,
        "_adv",
    )

    unmatched = merged["metres_gained"].isna()
    if unmatched.any():
        leftover_players = merged.loc[unmatched]
        player_counts = leftover_players.groupby(["date", "team", "last_name"]).size()
        adv_counts = adv.groupby(["date", "team", "last_name"]).size()
        unique_keys = player_counts[player_counts == 1].index.intersection(adv_counts[adv_counts == 1].index)
        if len(unique_keys) > 0:
            key_frame = pd.DataFrame(index=unique_keys).reset_index()
            key_frame.columns = ["date", "team", "last_name"]
            adv_last = (
                adv.merge(key_frame, on=["date", "team", "last_name"])
                [["date", "team", "last_name", *stat_cols]]
                .drop_duplicates(["date", "team", "last_name"], keep="first")
            )
            fallback = leftover_players.merge(
                adv_last, on=["date", "team", "last_name"], how="left", suffixes=("", "_fb")
            )
            for col in stat_cols:
                source = f"{col}_fb" if f"{col}_fb" in fallback.columns else col
                merged.loc[unmatched, col] = fallback[source].to_numpy()

    matched = merged["metres_gained"].notna().mean()
    print(f"Advanced stats matched {matched:.1%} of player-game rows")
    has_position = merged["player_position"].notna()
    merged["is_midfielder"] = pd.NA
    merged.loc[has_position, "is_midfielder"] = (
        merged.loc[has_position, "player_position"].isin(config.MIDFIELD_POSITIONS).astype(float)
    )
    return merged.drop(columns=["player_name", "last_name"], errors="ignore")
