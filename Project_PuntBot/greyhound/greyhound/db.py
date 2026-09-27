"""SQLite for greyhound Betfair rows only."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import config


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    return con


def init_db(db_path: Path | None = None) -> sqlite3.Connection:
    con = connect(db_path)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS betfair_runners (
            meeting_date TEXT NOT NULL,
            track TEXT NOT NULL,
            state_code TEXT,
            race_no INTEGER,
            win_market_id TEXT,
            win_market_name TEXT,
            racing_type TEXT,
            distance INTEGER,
            race_type TEXT,
            selection_id TEXT,
            tab_number INTEGER,
            selection_name TEXT,
            win_result TEXT,
            win_bsp REAL,
            win_bsp_volume REAL,
            win_preplay_max REAL,
            win_preplay_min REAL,
            win_preplay_ltp REAL,
            win_preplay_wap REAL,
            win_preplay_volume REAL,
            best_avail_back REAL,
            best_avail_lay REAL,
            back_overround REAL,
            lay_overround REAL,
            source_file TEXT,
            UNIQUE(win_market_id, selection_id)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_betfair_date_track "
        "ON betfair_runners(meeting_date, track, race_no, tab_number)"
    )
    con.commit()
    return con
