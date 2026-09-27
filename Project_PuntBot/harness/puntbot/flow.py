"""Load harness preplay prices and write the steam vs BSP report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import config
from common.flow import build_flow_report
from puntbot.db import init_db

FLOW_REPORT_PATH = config.FLOW_REPORT_PATH


def load_flow_runners(db_path: Path | None = None) -> pd.DataFrame:
    con = init_db(db_path)
    frame = pd.read_sql_query(
        """
        SELECT meeting_date, track, state_code, win_market_id, selection_name,
               win_result, win_bsp, win_preplay_ltp, win_preplay_wap,
               win_preplay_volume
        FROM betfair_runners
        WHERE win_bsp IS NOT NULL AND win_bsp > 1
          AND UPPER(COALESCE(state_code, '')) IN ('QLD','NSW','VIC','WA','SA','TAS','NT','ACT')
        """,
        con,
    )
    con.close()
    if frame.empty:
        return frame
    frame["won"] = frame["win_result"].astype(str).str.upper().eq("WINNER").astype(int)
    return frame


def write_flow_report(db_path: Path | None = None, out_path: Path | None = None) -> Path:
    dest = out_path or FLOW_REPORT_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    frame = load_flow_runners(db_path)
    text = build_flow_report(frame, "win_preplay_ltp")
    dest.write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {dest}")
    return dest


def main() -> None:
    write_flow_report()
