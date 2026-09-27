"""Download Betfair Automation Hub harness files and load them into SQLite."""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

import config
from puntbot.baseline import write_bsp_baseline
from puntbot.db import init_db, seed_track_codes

COLUMN_MAP = {
    "LOCAL_MEETING_DATE": "meeting_date",
    "TRACK": "track",
    "STATE_CODE": "state_code",
    "RACE_NO": "race_no",
    "WIN_MARKET_ID": "win_market_id",
    "WIN_MARKET_NAME": "win_market_name",
    "RACING_TYPE": "racing_type",
    "DISTANCE": "distance",
    "RACE_TYPE": "race_type",
    "SELECTION_ID": "selection_id",
    "TAB_NUMBER": "tab_number",
    "SELECTION_NAME": "selection_name",
    "WIN_RESULT": "win_result",
    "WIN_BSP": "win_bsp",
    "WIN_BSP_VOLUME": "win_bsp_volume",
    "WIN_PREPLAY_MAX_PRICE_TAKEN": "win_preplay_max",
    "WIN_PREPLAY_MIN_PRICE_TAKEN": "win_preplay_min",
    "WIN_PREPLAY_LAST_PRICE_TAKEN": "win_preplay_ltp",
    "WIN_PREPLAY_WEIGHTED_AVERAGE_PRICE_TAKEN": "win_preplay_wap",
    "WIN_PREPLAY_VOLUME": "win_preplay_volume",
    "BEST_AVAIL_BACK_AT_SCHEDULED_OFF": "best_avail_back",
    "BEST_AVAIL_LAY_AT_SCHEDULED_OFF": "best_avail_lay",
    "BACK_MARKET_PERCENTAGE_AT_SCHEDULED_OFF": "back_overround",
    "LAY_MARKET_PERCENTAGE_AT_SCHEDULED_OFF": "lay_overround",
}

HUB_FILES: list[str] = [
    *[f"ANZ_Harness_{year}.zip" for year in config.BETFAIR_YEARS],
    *[
        f"ANZ_Harness_{config.BETFAIR_MONTHLY_YEAR}_{month:02d}.csv"
        for month in range(1, config.BETFAIR_MONTHLY_THROUGH + 1)
    ],
]


def listed_hub_files() -> list[str]:
    return list(HUB_FILES)


def download_file(filename: str, dest_dir: Path, force: bool = False) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"Already have {filename}")
        return dest

    url = f"{config.BETFAIR_ASSETS_BASE}/{filename}"
    print(f"Downloading {url}")
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    dest.write_bytes(response.content)
    print(f"  saved {dest} ({len(response.content):,} bytes)")
    return dest


def download_hub_files(dest_dir: Path | None = None, force: bool = False) -> list[Path]:
    folder = dest_dir or config.BETFAIR_RAW_DIR
    return [download_file(name, folder, force=force) for name in listed_hub_files()]


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


def normalize_hub_frame(frame: pd.DataFrame, source_file: str) -> pd.DataFrame:
    renamed = frame.rename(columns={src: dest for src, dest in COLUMN_MAP.items() if src in frame.columns})
    keep = [col for col in COLUMN_MAP.values() if col in renamed.columns]
    out = renamed[keep].copy()
    out["source_file"] = source_file
    out["meeting_date"] = pd.to_datetime(out["meeting_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["win_market_id"] = out["win_market_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    out["selection_id"] = out["selection_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    if "state_code" in out.columns:
        out["state_code"] = out["state_code"].astype(str).str.upper().str.strip()
    numeric_cols = [
        "race_no",
        "distance",
        "tab_number",
        "win_bsp",
        "win_bsp_volume",
        "win_preplay_max",
        "win_preplay_min",
        "win_preplay_ltp",
        "win_preplay_wap",
        "win_preplay_volume",
        "best_avail_back",
        "best_avail_lay",
        "back_overround",
        "lay_overround",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["meeting_date", "track", "selection_name"])
    if "racing_type" in out.columns:
        racing = out["racing_type"].astype(str).str.lower()
        out = out[racing.str.contains("harness") | racing.eq("nan") | racing.eq("")]
    return out


def upsert_betfair_runners(con, frame: pd.DataFrame) -> int:
    columns = [
        "meeting_date",
        "track",
        "state_code",
        "race_no",
        "win_market_id",
        "win_market_name",
        "racing_type",
        "distance",
        "race_type",
        "selection_id",
        "tab_number",
        "selection_name",
        "win_result",
        "win_bsp",
        "win_bsp_volume",
        "win_preplay_max",
        "win_preplay_min",
        "win_preplay_ltp",
        "win_preplay_wap",
        "win_preplay_volume",
        "best_avail_back",
        "best_avail_lay",
        "back_overround",
        "lay_overround",
        "source_file",
    ]
    for col in columns:
        if col not in frame.columns:
            frame[col] = None
    records = frame[columns].where(pd.notnull(frame[columns]), None).itertuples(index=False, name=None)
    con.executemany(
        """
        INSERT INTO betfair_runners (
            meeting_date, track, state_code, race_no, win_market_id, win_market_name,
            racing_type, distance, race_type, selection_id, tab_number, selection_name,
            win_result, win_bsp, win_bsp_volume, win_preplay_max, win_preplay_min,
            win_preplay_ltp, win_preplay_wap, win_preplay_volume, best_avail_back,
            best_avail_lay, back_overround, lay_overround, source_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(win_market_id, selection_id) DO UPDATE SET
            meeting_date=excluded.meeting_date,
            track=excluded.track,
            state_code=excluded.state_code,
            race_no=excluded.race_no,
            win_market_name=excluded.win_market_name,
            racing_type=excluded.racing_type,
            distance=excluded.distance,
            race_type=excluded.race_type,
            tab_number=excluded.tab_number,
            selection_name=excluded.selection_name,
            win_result=excluded.win_result,
            win_bsp=excluded.win_bsp,
            win_bsp_volume=excluded.win_bsp_volume,
            win_preplay_max=excluded.win_preplay_max,
            win_preplay_min=excluded.win_preplay_min,
            win_preplay_ltp=excluded.win_preplay_ltp,
            win_preplay_wap=excluded.win_preplay_wap,
            win_preplay_volume=excluded.win_preplay_volume,
            best_avail_back=excluded.best_avail_back,
            best_avail_lay=excluded.best_avail_lay,
            back_overround=excluded.back_overround,
            lay_overround=excluded.lay_overround,
            source_file=excluded.source_file
        """,
        list(records),
    )
    con.commit()
    return len(frame)


def ingest_paths(paths: list[Path], db_path=None) -> int:
    con = init_db(db_path)
    seed_track_codes(con)
    total = 0
    for path in paths:
        print(f"Loading {path.name}")
        frame = normalize_hub_frame(load_hub_frame(path), path.name)
        inserted = upsert_betfair_runners(con, frame)
        total += inserted
        print(f"  {inserted:,} runner rows")
    con.close()
    return total


def run_ingest(force: bool = False, skip_download: bool = False, baseline: bool = True) -> None:
    config.BETFAIR_RAW_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = (
        sorted(config.BETFAIR_RAW_DIR.glob("ANZ_Harness_*"))
        if skip_download
        else download_hub_files(force=force)
    )
    if not paths:
        raise SystemExit("No Betfair hub files found. Re-run without --skip-download.")
    total = ingest_paths(paths)
    print(f"Ingested {total:,} runner rows into {config.DB_PATH}")
    if baseline:
        write_bsp_baseline()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Download and ingest Betfair harness CSVs")
    parser.add_argument("--force", action="store_true", help="Re-download files even if they exist")
    parser.add_argument("--skip-download", action="store_true", help="Load local files only")
    parser.add_argument("--no-baseline", action="store_true", help="Skip the BSP efficiency report")
    args = parser.parse_args(argv)
    run_ingest(force=args.force, skip_download=args.skip_download, baseline=not args.no_baseline)
