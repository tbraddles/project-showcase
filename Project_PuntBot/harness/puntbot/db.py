"""SQLite schema and connection helpers."""

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
    con.execute("PRAGMA foreign_keys=ON;")
    return con


def init_db(db_path: Path | None = None) -> sqlite3.Connection:
    con = connect(db_path)
    cur = con.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS races (
            date TEXT NOT NULL,
            race_id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_number INTEGER NOT NULL,
            track TEXT NOT NULL,
            track_rating TEXT,
            gross_time REAL,
            mile_rate REAL,
            lead_time REAL,
            first_quarter REAL,
            second_quarter REAL,
            third_quarter REAL,
            fourth_quarter REAL,
            margin_second REAL,
            margin_third REAL,
            UNIQUE(date, race_number, track)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS horse_results (
            date TEXT NOT NULL,
            track TEXT NOT NULL,
            race_id INTEGER NOT NULL,
            horse_name TEXT NOT NULL,
            place INTEGER,
            tab_number INTEGER,
            trainer TEXT,
            driver TEXT,
            starting_odds REAL,
            margin REAL,
            prize_money REAL,
            stewards_comments TEXT,
            form TEXT,
            row_and_barrier TEXT,
            post_race INTEGER,
            FOREIGN KEY(race_id) REFERENCES races(race_id) ON DELETE CASCADE,
            UNIQUE(race_id, horse_name, date, track)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS track_codes (
            code TEXT PRIMARY KEY,
            betfair_name TEXT NOT NULL,
            aliases TEXT
        )
        """
    )

    cur.execute(
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
            place_result TEXT,
            place_bsp REAL,
            place_market_id TEXT,
            place_bsp_volume REAL,
            place_preplay_volume REAL,
            UNIQUE(win_market_id, selection_id)
        )
        """
    )
    existing = {row[1] for row in con.execute("PRAGMA table_info(betfair_runners)")}
    for name, typ in (
        ("place_result", "TEXT"),
        ("place_bsp", "REAL"),
        ("place_market_id", "TEXT"),
        ("place_bsp_volume", "REAL"),
        ("place_preplay_volume", "REAL"),
    ):
        if name not in existing:
            con.execute(f"ALTER TABLE betfair_runners ADD COLUMN {name} {typ}")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS runner_matches (
            race_id INTEGER NOT NULL,
            horse_name TEXT NOT NULL,
            meeting_date TEXT NOT NULL,
            track_code TEXT,
            tab_number INTEGER,
            win_market_id TEXT NOT NULL,
            selection_id TEXT NOT NULL,
            match_method TEXT NOT NULL,
            UNIQUE(race_id, horse_name),
            FOREIGN KEY(race_id) REFERENCES races(race_id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_horse_results_date ON horse_results(date, track)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_betfair_date_track ON betfair_runners(meeting_date, track, race_no, tab_number)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_races_date_track ON races(date, track, race_number)"
    )
    con.commit()
    return con


def seed_track_codes(con: sqlite3.Connection) -> None:
    from puntbot.tracks import load_track_rows

    rows = [(row["code"].upper(), row["betfair_name"], row.get("aliases")) for row in load_track_rows()]
    con.executemany(
        """
        INSERT INTO track_codes (code, betfair_name, aliases)
        VALUES (?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            betfair_name=excluded.betfair_name,
            aliases=excluded.aliases
        """,
        rows,
    )
    con.commit()


def existing_form_meetings(con: sqlite3.Connection) -> set[tuple[str, str]]:
    cur = con.execute("SELECT DISTINCT date, track FROM races")
    return {(row["date"], row["track"]) for row in cur.fetchall()}


def upsert_race(con: sqlite3.Connection, race_time: dict) -> int:
    cur = con.cursor()
    date = race_time["date"]
    race_number = race_time["race"]
    track = race_time.get("track")

    cur.execute(
        """
        INSERT INTO races (
            date, race_number, track, track_rating, gross_time, mile_rate, lead_time,
            first_quarter, second_quarter, third_quarter, fourth_quarter,
            margin_second, margin_third
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date, race_number, track) DO UPDATE SET
            track_rating=excluded.track_rating,
            gross_time=excluded.gross_time,
            mile_rate=excluded.mile_rate,
            lead_time=excluded.lead_time,
            first_quarter=excluded.first_quarter,
            second_quarter=excluded.second_quarter,
            third_quarter=excluded.third_quarter,
            fourth_quarter=excluded.fourth_quarter,
            margin_second=excluded.margin_second,
            margin_third=excluded.margin_third
        """,
        (
            date,
            race_number,
            track,
            race_time.get("track_rating"),
            race_time.get("gross_time"),
            race_time.get("mile_rate"),
            race_time.get("lead_time"),
            race_time.get("first_quarter"),
            race_time.get("second_quarter"),
            race_time.get("third_quarter"),
            race_time.get("fourth_quarter"),
            race_time.get("margin_second"),
            race_time.get("margin_third"),
        ),
    )
    cur.execute(
        "SELECT race_id FROM races WHERE date=? AND race_number=? AND track=?",
        (date, race_number, track),
    )
    return cur.fetchone()[0]


def upsert_horse_result(con: sqlite3.Connection, horse: dict, race_id: int) -> None:
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO horse_results (
            date, track, race_id, horse_name, place, tab_number, trainer, driver,
            starting_odds, margin, prize_money, stewards_comments, form,
            row_and_barrier, post_race
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(race_id, horse_name, date, track) DO UPDATE SET
            place=excluded.place,
            tab_number=excluded.tab_number,
            trainer=excluded.trainer,
            driver=excluded.driver,
            starting_odds=excluded.starting_odds,
            margin=excluded.margin,
            prize_money=excluded.prize_money,
            stewards_comments=excluded.stewards_comments,
            form=excluded.form,
            row_and_barrier=excluded.row_and_barrier,
            post_race=excluded.post_race
        """,
        (
            horse.get("date"),
            horse.get("track"),
            race_id,
            horse.get("horse_name"),
            horse.get("place"),
            horse.get("tab_number"),
            horse.get("trainer"),
            horse.get("driver"),
            horse.get("starting_odds"),
            horse.get("margin"),
            horse.get("prize_money"),
            horse.get("stewards_comments"),
            horse.get("form"),
            horse.get("row_and_barrier"),
            1 if horse.get("post_race") else 0,
        ),
    )


def ingest_form_rows(
    con: sqlite3.Connection,
    master_horse_results: list[dict],
    master_race_times: list[dict],
) -> None:
    from datetime import datetime

    race_id_map: dict[tuple[str, int, str], int] = {}
    for race_time in master_race_times:
        if isinstance(race_time.get("date"), datetime):
            race_time["date"] = race_time["date"].strftime("%Y-%m-%d")
        race_id = upsert_race(con, race_time)
        race_id_map[(race_time["date"], race_time["race"], race_time.get("track"))] = race_id

    for horse in master_horse_results:
        date = horse.get("date")
        if isinstance(date, datetime):
            horse["date"] = date.strftime("%Y-%m-%d")
        key = (horse.get("date"), horse.get("race"), horse.get("track"))
        race_id = race_id_map.get(key)
        if race_id is None:
            print(f"Warning: no race_times for horse entry {key}, skipping.")
            continue
        upsert_horse_result(con, horse, race_id)
    con.commit()
