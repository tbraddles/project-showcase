"""Betfair Automation Hub CSV/zip helpers."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

COLUMN_MAP = {
    "LOCAL_MEETING_DATE": "meeting_date",
    "TRACK": "track",
    "STATE_CODE": "state_code",
    "RACE_NO": "race_no",
    "WIN_MARKET_ID": "win_market_id",
    "WIN_MARKET_NAME": "win_market_name",
    "PLACE_MARKET_ID": "place_market_id",
    "RACING_TYPE": "racing_type",
    "DISTANCE": "distance",
    "RACE_TYPE": "race_type",
    "SELECTION_ID": "selection_id",
    "TAB_NUMBER": "tab_number",
    "SELECTION_NAME": "selection_name",
    "WIN_RESULT": "win_result",
    "WIN_BSP": "win_bsp",
    "PLACE_RESULT": "place_result",
    "PLACE_BSP": "place_bsp",
    "WIN_BSP_VOLUME": "win_bsp_volume",
    "WIN_PREPLAY_MAX_PRICE_TAKEN": "win_preplay_max",
    "WIN_PREPLAY_MIN_PRICE_TAKEN": "win_preplay_min",
    "WIN_PREPLAY_LAST_PRICE_TAKEN": "win_preplay_ltp",
    "WIN_PREPLAY_WEIGHTED_AVERAGE_PRICE_TAKEN": "win_preplay_wap",
    "WIN_PREPLAY_VOLUME": "win_preplay_volume",
    "PLACE_BSP_VOLUME": "place_bsp_volume",
    "PLACE_PREPLAY_VOLUME": "place_preplay_volume",
    "BEST_AVAIL_BACK_AT_SCHEDULED_OFF": "best_avail_back",
    "BEST_AVAIL_LAY_AT_SCHEDULED_OFF": "best_avail_lay",
    "BACK_MARKET_PERCENTAGE_AT_SCHEDULED_OFF": "back_overround",
    "LAY_MARKET_PERCENTAGE_AT_SCHEDULED_OFF": "lay_overround",
}

ASSETS_BASE = "https://betfair-datascientists.github.io/data/assets"


def parse_meeting_date(series: pd.Series) -> pd.Series:
    """Hub files mix ISO dates (2025-08-01) with day-first slashes (1/07/2025)."""
    text = series.astype(str).str.strip()
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    slash = text.str.contains("/", na=False)
    if slash.any():
        parsed.loc[slash] = pd.to_datetime(text.loc[slash], dayfirst=True, errors="coerce")
    if (~slash).any():
        parsed.loc[~slash] = pd.to_datetime(text.loc[~slash], errors="coerce")
    return parsed


def download_file(filename: str, dest_dir: Path, force: bool = False) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"Already have {filename}")
        return dest

    url = f"{ASSETS_BASE}/{filename}"
    print(f"Downloading {url}")
    response = requests.get(url, timeout=180)
    response.raise_for_status()
    dest.write_bytes(response.content)
    print(f"  saved {dest} ({len(response.content):,} bytes)")
    return dest


def _read_csv_bytes(raw: bytes, source_name: str) -> pd.DataFrame:
    frame = pd.read_csv(io.BytesIO(raw), low_memory=False)
    frame.columns = [str(col).strip().upper() for col in frame.columns]
    missing = [col for col in ("LOCAL_MEETING_DATE", "TRACK", "SELECTION_NAME") if col not in frame.columns]
    if missing:
        raise ValueError(f"{source_name} missing expected columns: {missing}")
    return frame


def load_hub_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        frames = []
        with zipfile.ZipFile(path) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError(f"{path.name} contains no CSV files")
            for name in csv_names:
                frames.append(_read_csv_bytes(archive.read(name), f"{path.name}:{name}"))
        return pd.concat(frames, ignore_index=True)
    return _read_csv_bytes(path.read_bytes(), path.name)


def normalize_hub_frame(
    frame: pd.DataFrame,
    source_file: str,
    racing_type_contains: str | None = None,
) -> pd.DataFrame:
    renamed = frame.rename(columns={src: dest for src, dest in COLUMN_MAP.items() if src in frame.columns})
    keep = [col for col in COLUMN_MAP.values() if col in renamed.columns]
    out = renamed[keep].copy()
    out["source_file"] = source_file
    out["meeting_date"] = parse_meeting_date(out["meeting_date"]).dt.strftime("%Y-%m-%d")
    out["win_market_id"] = out["win_market_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    out["selection_id"] = out["selection_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    if "state_code" in out.columns:
        out["state_code"] = out["state_code"].astype(str).str.upper().str.strip()
    for col in (
        "race_no",
        "distance",
        "tab_number",
        "win_bsp",
        "place_bsp",
        "win_bsp_volume",
        "place_bsp_volume",
        "place_preplay_volume",
        "win_preplay_max",
        "win_preplay_min",
        "win_preplay_ltp",
        "win_preplay_wap",
        "win_preplay_volume",
        "best_avail_back",
        "best_avail_lay",
        "back_overround",
        "lay_overround",
    ):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["meeting_date", "track", "selection_name"])
    if racing_type_contains and "racing_type" in out.columns:
        racing = out["racing_type"].astype(str).str.lower()
        wanted = racing_type_contains.lower()
        out = out[racing.str.contains(wanted) | racing.eq("nan") | racing.eq("")]
    return out
