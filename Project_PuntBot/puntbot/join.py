"""Join harness.org.au form rows to Betfair runners."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

import config
from puntbot.db import init_db, seed_track_codes
from puntbot.names import normalize_horse_name
from puntbot.tracks import canonical_code, display_venue


def load_form(con) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT
            hr.race_id,
            hr.date AS meeting_date,
            hr.track AS track_code,
            r.race_number,
            hr.horse_name,
            hr.place,
            hr.tab_number,
            hr.trainer,
            hr.driver,
            hr.starting_odds,
            hr.margin,
            hr.prize_money,
            hr.form,
            hr.row_and_barrier,
            hr.stewards_comments,
            r.track_rating,
            r.mile_rate,
            r.gross_time,
            r.lead_time,
            r.first_quarter,
            r.second_quarter,
            r.third_quarter,
            r.fourth_quarter
        FROM horse_results hr
        JOIN races r ON r.race_id = hr.race_id
        """,
        con,
    )


def load_betfair(con) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT
            meeting_date,
            track,
            state_code,
            race_no,
            win_market_id,
            win_market_name,
            distance,
            race_type,
            selection_id,
            tab_number,
            selection_name,
            win_result,
            win_bsp,
            win_bsp_volume,
            win_preplay_ltp,
            win_preplay_wap,
            win_preplay_volume,
            best_avail_back,
            best_avail_lay
        FROM betfair_runners
        WHERE UPPER(COALESCE(state_code, '')) IN ('QLD','NSW','VIC','WA','SA','TAS','NT','ACT')
        """,
        con,
    )


def prepare_frames(form: pd.DataFrame, betfair: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    form = form.copy()
    betfair = betfair.copy()
    form["track_code"] = form["track_code"].astype(str).str.upper()
    form["venue"] = form["track_code"].map(display_venue)
    form["join_code"] = form["track_code"].map(lambda code: canonical_code(code) or code)
    form["name_key"] = form["horse_name"].map(normalize_horse_name)
    form["tab_number"] = pd.to_numeric(form["tab_number"], errors="coerce")
    form["race_number"] = pd.to_numeric(form["race_number"], errors="coerce")

    betfair["join_code"] = betfair["track"].map(canonical_code)
    betfair["name_key"] = betfair["selection_name"].map(normalize_horse_name)
    betfair["tab_number"] = pd.to_numeric(betfair["tab_number"], errors="coerce")
    betfair["race_no"] = pd.to_numeric(betfair["race_no"], errors="coerce")
    return form, betfair


def _attach(matches: pd.DataFrame, method: str) -> pd.DataFrame:
    keep = matches[
        [
            "race_id",
            "horse_name",
            "meeting_date",
            "track_code",
            "tab_number",
            "win_market_id",
            "selection_id",
        ]
    ].copy()
    keep["match_method"] = method
    return keep.drop_duplicates(subset=["race_id", "horse_name"])


def match_runners(form: pd.DataFrame, betfair: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    form, betfair = prepare_frames(form, betfair)
    unmatched = form.copy()
    pieces: list[pd.DataFrame] = []
    stats = {"form_runners": len(form), "betfair_au_runners": len(betfair)}

    tab_keys = ["meeting_date", "join_code", "race_number", "tab_number"]
    bf_tab = betfair.rename(columns={"race_no": "race_number"})
    tab_merge = unmatched.merge(
        bf_tab,
        on=tab_keys,
        how="inner",
        suffixes=("", "_bf"),
    )
    tab_merge = tab_merge[tab_merge["tab_number"].notna() & tab_merge["join_code"].notna()]
    pieces.append(_attach(tab_merge, "exact_tab"))
    matched_ids = set(zip(tab_merge["race_id"], tab_merge["horse_name"]))
    unmatched = unmatched[~unmatched.apply(lambda row: (row["race_id"], row["horse_name"]) in matched_ids, axis=1)]

    name_keys = ["meeting_date", "join_code", "name_key"]
    name_merge = unmatched.merge(betfair, on=name_keys, how="inner", suffixes=("", "_bf"))
    name_merge = name_merge[name_merge["join_code"].notna() & name_merge["name_key"].ne("")]
    if not name_merge.empty and "race_number" in name_merge.columns and "race_no" in name_merge.columns:
        name_merge = name_merge.copy()
        name_merge["_race_match"] = name_merge["race_number"].eq(name_merge["race_no"]).astype(int)
        name_merge = name_merge.sort_values(
            ["race_id", "horse_name", "_race_match"],
            ascending=[True, True, False],
        )
        name_merge = name_merge.drop(columns=["_race_match"])
    name_merge = name_merge.drop_duplicates(subset=["race_id", "horse_name"])
    pieces.append(_attach(name_merge, "normalized_name"))

    matches = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
    if not matches.empty:
        matches = matches.drop_duplicates(subset=["race_id", "horse_name"], keep="first")
    stats["matched"] = 0 if matches.empty else len(matches)
    stats["exact_tab"] = 0 if matches.empty else int(matches["match_method"].eq("exact_tab").sum())
    stats["normalized_name"] = 0 if matches.empty else int(matches["match_method"].eq("normalized_name").sum())
    stats["unmatched"] = stats["form_runners"] - stats["matched"]
    stats["unmapped_form_tracks"] = int(form["join_code"].isna().sum()) if "join_code" in form else 0
    stats["unmapped_betfair_tracks"] = int(betfair["join_code"].isna().sum())
    return matches, stats


def persist_matches(con, matches: pd.DataFrame) -> None:
    con.execute("DELETE FROM runner_matches")
    if matches.empty:
        con.commit()
        return
    rows = matches[
        [
            "race_id",
            "horse_name",
            "meeting_date",
            "track_code",
            "tab_number",
            "win_market_id",
            "selection_id",
            "match_method",
        ]
    ].itertuples(index=False, name=None)
    con.executemany(
        """
        INSERT INTO runner_matches (
            race_id, horse_name, meeting_date, track_code, tab_number,
            win_market_id, selection_id, match_method
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        list(rows),
    )
    con.commit()


def write_join_report(stats: dict[str, int], unmatched: pd.DataFrame, path: Path | None = None) -> Path:
    dest = path or config.JOIN_REPORT_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    matched = stats.get("matched", 0)
    total = stats.get("form_runners", 0)
    rate = (matched / total) if total else 0.0
    lines = [
        "PuntBot form-to-Betfair join report",
        "",
        f"Form runners: {total:,}",
        f"Betfair AU runners: {stats.get('betfair_au_runners', 0):,}",
        f"Matched: {matched:,} ({rate:.1%})",
        f"  exact_tab: {stats.get('exact_tab', 0):,}",
        f"  normalized_name: {stats.get('normalized_name', 0):,}",
        f"Unmatched: {stats.get('unmatched', 0):,}",
        f"Form rows with unknown track code: {stats.get('unmapped_form_tracks', 0):,}",
        f"Betfair rows with unknown venue: {stats.get('unmapped_betfair_tracks', 0):,}",
        "",
        "Unmatched form runners (first 50):",
    ]
    if unmatched.empty:
        lines.append("  none")
    else:
        preview = unmatched.head(50)
        for row in preview.itertuples(index=False):
            lines.append(
                f"  {row.meeting_date} {row.track_code} R{row.race_number} "
                f"#{row.tab_number} {row.horse_name}"
            )
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(dest.read_text(encoding="utf-8"))
    return dest


def run_join(db_path=None) -> pd.DataFrame:
    con = init_db(db_path)
    seed_track_codes(con)
    form = load_form(con)
    betfair = load_betfair(con)
    matches, stats = match_runners(form, betfair)
    persist_matches(con, matches)

    matched_keys = set(zip(matches["race_id"], matches["horse_name"])) if not matches.empty else set()
    unmatched = form[~form.apply(lambda row: (row["race_id"], row["horse_name"]) in matched_keys, axis=1)]
    write_join_report(stats, unmatched)
    con.close()
    return matches


def load_joined(db_path=None) -> pd.DataFrame:
    con = init_db(db_path)
    frame = pd.read_sql_query(
        """
        SELECT
            hr.race_id,
            hr.date AS meeting_date,
            hr.track AS track_code,
            r.race_number,
            hr.horse_name,
            hr.place,
            hr.tab_number,
            hr.trainer,
            hr.driver,
            hr.margin,
            hr.prize_money,
            hr.form,
            hr.row_and_barrier,
            r.track_rating,
            r.mile_rate,
            r.gross_time,
            rm.match_method,
            bf.win_market_id,
            bf.selection_id,
            bf.selection_name,
            bf.track AS betfair_track,
            bf.state_code,
            bf.distance,
            bf.race_type,
            bf.win_result,
            bf.win_bsp,
            bf.win_bsp_volume,
            bf.win_preplay_volume,
            bf.win_preplay_wap,
            bf.best_avail_back
        FROM runner_matches rm
        JOIN horse_results hr
          ON hr.race_id = rm.race_id AND hr.horse_name = rm.horse_name
        JOIN races r ON r.race_id = hr.race_id
        JOIN betfair_runners bf
          ON bf.win_market_id = rm.win_market_id AND bf.selection_id = rm.selection_id
        """,
        con,
    )
    con.close()
    return frame


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Join form results to Betfair runners")
    parser.parse_args(argv)
    run_join()
