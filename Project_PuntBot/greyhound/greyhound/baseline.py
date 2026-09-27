"""Greyhound BSP efficiency. No form model."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import config
from common.baseline import AU_STATES, build_baseline_text
from greyhound.db import init_db


def load_au_win_runners(db_path: Path | None = None) -> pd.DataFrame:
    con = init_db(db_path)
    frame = pd.read_sql_query(
        """
        SELECT meeting_date, track, state_code, race_no, win_market_id, selection_name,
               tab_number, win_result, win_bsp, win_bsp_volume, win_preplay_volume
        FROM betfair_runners
        WHERE win_bsp IS NOT NULL
          AND win_bsp > 1
          AND UPPER(COALESCE(state_code, '')) IN ('QLD','NSW','VIC','WA','SA','TAS','NT','ACT')
        """,
        con,
    )
    con.close()
    if frame.empty:
        return frame
    frame["won"] = frame["win_result"].astype(str).str.upper().eq("WINNER").astype(int)
    frame["implied"] = 1.0 / frame["win_bsp"]
    return frame


def write_bsp_baseline(db_path: Path | None = None, out_path: Path | None = None) -> Path:
    dest = out_path or config.BASELINE_REPORT_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = build_baseline_text(load_au_win_runners(db_path), "greyhound")
    dest.write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {dest}")
    return dest
