"""Download Aus/NZ Greyhound Hub files and load Australian win rows."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

import config
from common.hub import download_file, load_hub_frame, normalize_hub_frame
from greyhound.baseline import write_bsp_baseline
from greyhound.db import init_db

HUB_FILES: list[str] = [
    *[f"ANZ_Greyhounds_{year}.zip" for year in config.BETFAIR_YEARS],
    *[
        f"ANZ_Greyhounds_{config.BETFAIR_MONTHLY_YEAR}_{month:02d}.csv"
        for month in range(1, config.BETFAIR_MONTHLY_THROUGH + 1)
    ],
]


def download_hub_files(dest_dir: Path | None = None, force: bool = False) -> list[Path]:
    folder = dest_dir or config.BETFAIR_RAW_DIR
    return [download_file(name, folder, force=force) for name in HUB_FILES]


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
            win_bsp=excluded.win_bsp,
            win_result=excluded.win_result,
            win_preplay_volume=excluded.win_preplay_volume,
            source_file=excluded.source_file
        """,
        list(records),
    )
    con.commit()
    return len(frame)


def ingest_paths(paths: list[Path], db_path=None) -> int:
    con = init_db(db_path)
    total = 0
    for path in paths:
        print(f"Loading {path.name}")
        frame = normalize_hub_frame(load_hub_frame(path), path.name, racing_type_contains="grey")
        inserted = upsert_betfair_runners(con, frame)
        total += inserted
        print(f"  {inserted:,} runner rows")
    con.close()
    return total


def run_ingest(force: bool = False, skip_download: bool = False, baseline: bool = True) -> None:
    config.BETFAIR_RAW_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = (
        sorted(config.BETFAIR_RAW_DIR.glob("ANZ_Greyhounds_*"))
        if skip_download
        else download_hub_files(force=force)
    )
    if not paths:
        raise SystemExit("No greyhound Hub files found.")
    total = ingest_paths(paths)
    print(f"Ingested {total:,} runner rows into {config.DB_PATH}")
    if baseline:
        write_bsp_baseline()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Download and ingest Betfair greyhound CSVs")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--no-baseline", action="store_true")
    args = parser.parse_args(argv)
    run_ingest(force=args.force, skip_download=args.skip_download, baseline=not args.no_baseline)
