"""Harness place vs win-BSP report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import config
from common.place import build_place_report, placed_flag
from puntbot.db import init_db

PLACE_REPORT_PATH = config.PLACE_REPORT_PATH


def load_place_runners(db_path: Path | None = None) -> pd.DataFrame:
    con = init_db(db_path)
    try:
        frame = pd.read_sql_query(
            """
            SELECT meeting_date, track, state_code, win_market_id, selection_name,
                   win_bsp, place_bsp, place_result, win_result,
                   place_bsp_volume, place_preplay_volume
            FROM betfair_runners
            WHERE win_bsp IS NOT NULL AND win_bsp > 1
              AND place_bsp IS NOT NULL AND place_bsp > 1
              AND UPPER(COALESCE(state_code, '')) IN ('QLD','NSW','VIC','WA','SA','TAS','NT','ACT')
            """,
            con,
        )
    except Exception as exc:  # noqa: BLE001
        con.close()
        raise SystemExit(
            "Place columns are missing. Re-run: python 01_ingest_betfair.py --skip-download --no-baseline"
        ) from exc
    con.close()
    if frame.empty:
        return frame
    frame["placed"] = placed_flag(frame["place_result"])
    return frame


def write_place_report(db_path: Path | None = None, out_path: Path | None = None) -> Path:
    dest = out_path or PLACE_REPORT_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = build_place_report(load_place_runners(db_path), "harness")
    dest.write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {dest}")
    return dest


def main() -> None:
    write_place_report()
