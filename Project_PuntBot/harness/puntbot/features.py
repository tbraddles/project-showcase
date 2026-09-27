"""Pre-race form features. No Betfair prices are used as predictors.

Feature groups follow the form factors in Considerations.md:
race conditions, speed maps, recent form, sectionals, distance,
trainer/driver, sprint lanes, barriers, and stewards excuses.
"""

from __future__ import annotations

import argparse
import re

import numpy as np
import pandas as pd

import config
from puntbot.join import load_joined
from puntbot.names import normalize_horse_name
from puntbot.tracks import track_is_metro, track_sprint_lane

_TOKEN_SPLIT = re.compile(r"[^A-Z0-9/]+")


def parse_barrier(row_and_barrier: str | None) -> float:
    if row_and_barrier is None or (isinstance(row_and_barrier, float) and np.isnan(row_and_barrier)):
        return np.nan
    numbers = re.findall(r"\d+", str(row_and_barrier))
    if not numbers:
        return np.nan
    return float(numbers[-1])


def parse_front_row(row_and_barrier: str | None) -> float:
    if row_and_barrier is None or (isinstance(row_and_barrier, float) and np.isnan(row_and_barrier)):
        return np.nan
    text = str(row_and_barrier).strip().lower()
    if text.startswith("fr") or text.startswith("front"):
        return 1.0
    if text.startswith("sr") or text.startswith("second"):
        return 0.0
    return np.nan


def _comment_tokens(comments: str | None) -> set[str]:
    if comments is None or (isinstance(comments, float) and np.isnan(comments)):
        return set()
    return {token for token in _TOKEN_SPLIT.split(str(comments).upper()) if token}


def parse_stewards_flags(comments: str | None) -> dict[str, int]:
    tokens = _comment_tokens(comments)
    led = int("L" in tokens or "L1W" in tokens)
    death = int("OL" in tokens or "L1W" in tokens)
    trail = int(bool(tokens & {"OTE", "OTM", "TL"}))
    gate_speed = int("GS" in tokens)
    three_wide = int(any(token.startswith("3W") for token in tokens))
    used_lane = int("USL" in tokens)
    held_up = int(bool(tokens & {"INC", "NCR", "HU", "CHK"}))
    broke = int(bool(tokens & {"BAS", "BRK", "GAL"}))
    tyre = int(any("T/" in token or token in {"TYRE", "RFTNG"} for token in tokens))
    lame = int(bool(tokens & {"LAME", "INJ", "BLEED", "BLED"}))
    return {
        "led": led,
        "death": death,
        "trail": trail,
        "gate_speed": gate_speed,
        "three_wide": three_wide,
        "used_lane": used_lane,
        "held_up": held_up,
        "broke": broke,
        "tyre": tyre,
        "lame": lame,
    }


def parse_grade(market_name: str | None) -> float:
    """Betfair Hub names end in M (metro) or S (provincial/country)."""
    if not market_name:
        return np.nan
    match = re.search(r"\b([MS])\b\s*$", str(market_name).strip(), flags=re.IGNORECASE)
    if not match:
        return np.nan
    return 1.0 if match.group(1).upper() == "M" else 0.0


def distance_band(distance: float) -> float:
    if pd.isna(distance):
        return np.nan
    if distance <= 1760:
        return 0.0
    if distance <= 2300:
        return 1.0
    return 2.0


def inside_draw_score(front_row: float, barrier: float) -> float:
    if pd.isna(barrier):
        return np.nan
    if front_row == 1:
        if barrier <= 1:
            return 1.00
        if barrier <= 2:
            return 0.85
        if barrier <= 4:
            return 0.55
        return 0.25
    if front_row == 0:
        return 0.35 if barrier <= 2 else 0.15
    if barrier <= 2:
        return 0.70
    if barrier <= 4:
        return 0.40
    return 0.20


METRES_PER_SECOND = 14.0
SOLONSCH_GUIDELINE = 0.3
SOLONSCH_HARD_GAP = 1.5
SOLONSCH_SOFT_GAP = 0.8


def adjusted_half_mile(last_half: float, margin: float | None) -> float:
    """Solonsch: last-half time plus beaten metres / 14 m/s. Ignore 20m+ blowouts."""
    if last_half is None or (isinstance(last_half, float) and np.isnan(last_half)):
        return np.nan
    beaten = 0.0 if margin is None or (isinstance(margin, float) and np.isnan(margin)) else max(0.0, float(margin))
    if beaten >= 20:
        return np.nan
    return float(last_half) + beaten / METRES_PER_SECOND


def add_solonsch_ratings(frame: pd.DataFrame) -> pd.DataFrame:
    """Last-three adjusted half-mile ratings and a race-level cull, all from prior starts."""
    ordered = frame.sort_values(["meeting_date", "race_number", "horse_key"], kind="mergesort")
    ordered["adjusted_half"] = [
        adjusted_half_mile(half, margin) for half, margin in zip(ordered["last_half"], ordered["margin"])
    ]
    grouped = ordered.groupby("horse_key", dropna=False, sort=False)
    for lag in (1, 2, 3):
        ordered[f"_ah{lag}"] = grouped["adjusted_half"].shift(lag)
    ordered["speed_rating"] = ordered[["_ah1", "_ah2", "_ah3"]].mean(axis=1)
    ordered["speed_samples"] = ordered[["_ah1", "_ah2", "_ah3"]].notna().sum(axis=1)
    ordered["race_best_speed"] = ordered.groupby("win_market_id")["speed_rating"].transform("min")
    ordered["speed_gap"] = ordered["speed_rating"] - ordered["race_best_speed"]
    ordered["speed_discard"] = ordered["speed_gap"].gt(SOLONSCH_GUIDELINE + SOLONSCH_HARD_GAP).astype(float)
    soft = ordered["speed_gap"].between(
        SOLONSCH_GUIDELINE + SOLONSCH_SOFT_GAP,
        SOLONSCH_GUIDELINE + SOLONSCH_HARD_GAP,
        inclusive="left",
    )
    poor_form = ordered["horse_places_l5"].fillna(0).eq(0) & ordered["horse_starts_l5"].fillna(0).ge(3)
    bad_draw = ordered["front_row"].eq(0) | ordered["barrier"].ge(7)
    ordered["speed_soft_discard"] = (soft & (poor_form | bad_draw)).astype(float)
    score = -ordered["speed_rating"]
    score = score.where(ordered["speed_discard"].eq(0))
    weight = np.exp(score - score.groupby(ordered["win_market_id"]).transform("max"))
    totals = weight.groupby(ordered["win_market_id"]).transform("sum")
    ordered["solonsch_p"] = np.where(totals > 0, weight / totals, np.nan)
    ordered["speed_rank"] = ordered.groupby("win_market_id")["speed_rating"].rank(method="min")
    return ordered.drop(columns=["_ah1", "_ah2", "_ah3"])


def _prior_rate(wins: pd.Series, starts: pd.Series) -> pd.Series:
    return np.where(starts > 0, wins / starts, np.nan)


def add_entity_history(frame: pd.DataFrame, key: str, prefix: str) -> pd.DataFrame:
    ordered = frame.sort_values(["meeting_date", "race_number", key], kind="mergesort")
    grouped = ordered.groupby(key, dropna=False, sort=False)
    won = ordered["won"]
    place = ordered["place"]
    ordered[f"{prefix}_starts_prior"] = grouped.cumcount()
    ordered[f"{prefix}_wins_prior"] = grouped[won.name].cumsum() - won
    if prefix == "horse":
        placed = place.le(3) & place.gt(0)
        ordered["_placed"] = placed.astype(int)
        ordered[f"{prefix}_places_prior"] = grouped["_placed"].cumsum() - ordered["_placed"]
        ordered[f"{prefix}_place_sum_prior"] = grouped[place.name].cumsum() - place
        ordered[f"{prefix}_avg_place_prior"] = np.where(
            ordered[f"{prefix}_starts_prior"] > 0,
            ordered[f"{prefix}_place_sum_prior"] / ordered[f"{prefix}_starts_prior"],
            np.nan,
        )
        last_date = grouped["meeting_date"].shift(1)
        ordered["days_since_last"] = (
            pd.to_datetime(ordered["meeting_date"]) - pd.to_datetime(last_date)
        ).dt.days
        ordered["last_place"] = grouped[place.name].shift(1)
        for window in (5,):
            starts_l5 = grouped.cumcount().clip(upper=window)
            wins_l5 = grouped[won.name].transform(lambda s: s.shift(1).rolling(window, min_periods=1).sum())
            places_l5 = grouped["_placed"].transform(lambda s: s.shift(1).rolling(window, min_periods=1).sum())
            avg_place_l5 = grouped[place.name].transform(
                lambda s: s.shift(1).rolling(window, min_periods=1).mean()
            )
            ordered[f"{prefix}_starts_l{window}"] = starts_l5
            ordered[f"{prefix}_wins_l{window}"] = wins_l5
            ordered[f"{prefix}_places_l{window}"] = places_l5
            ordered[f"{prefix}_avg_place_l{window}"] = avg_place_l5
        ordered = ordered.drop(columns=["_placed", f"{prefix}_place_sum_prior"])
    ordered[f"{prefix}_win_rate_prior"] = _prior_rate(
        ordered[f"{prefix}_wins_prior"], ordered[f"{prefix}_starts_prior"]
    )
    return ordered


def add_shifted_history(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    ordered = frame.sort_values(["meeting_date", "race_number", "horse_key"], kind="mergesort")
    grouped = ordered.groupby("horse_key", dropna=False, sort=False)
    for column in columns:
        ordered[f"last_{column}"] = grouped[column].shift(1)
        if column in {"led", "death", "trail", "gate_speed", "three_wide", "used_lane", "held_up", "broke", "tyre"}:
            prior_sum = grouped[column].cumsum() - ordered[column]
            ordered[f"{column}_rate_prior"] = _prior_rate(prior_sum, ordered["horse_starts_prior"])
    return ordered


def add_distance_form(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.sort_values(["meeting_date", "race_number", "horse_key"], kind="mergesort")
    same_band_win = []
    same_band_starts = []
    for _, group in ordered.groupby("horse_key", dropna=False, sort=False):
        wins = []
        starts = []
        band_wins = {0.0: 0, 1.0: 0, 2.0: 0}
        band_starts = {0.0: 0, 1.0: 0, 2.0: 0}
        for row in group.itertuples(index=False):
            band = row.dist_band
            if pd.isna(band):
                wins.append(np.nan)
                starts.append(np.nan)
            else:
                wins.append(band_wins.get(band, 0))
                starts.append(band_starts.get(band, 0))
                band_starts[band] = band_starts.get(band, 0) + 1
                band_wins[band] = band_wins.get(band, 0) + int(row.won)
        same_band_win.extend(wins)
        same_band_starts.extend(starts)
    ordered["same_dist_wins_prior"] = same_band_win
    ordered["same_dist_starts_prior"] = same_band_starts
    ordered["same_dist_win_rate_prior"] = _prior_rate(
        pd.to_numeric(ordered["same_dist_wins_prior"], errors="coerce"),
        pd.to_numeric(ordered["same_dist_starts_prior"], errors="coerce"),
    )
    return ordered


def add_speed_map(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    lead_rate = out["led_rate_prior"].fillna(0) + 0.35 * out["gate_speed_rate_prior"].fillna(0)
    breeze_rate = out["death_rate_prior"].fillna(0)
    draw = out["inside_draw_score"].fillna(0.25)
    out["lead_score"] = lead_rate * draw
    out["breeze_score"] = breeze_rate * np.where(out["front_row"].fillna(1).eq(0), 0.7, 1.0)
    out["lead_rank"] = out.groupby("win_market_id")["lead_score"].rank(ascending=False, method="first")
    out["is_mapped_leader"] = out["lead_rank"].eq(1).astype(int)
    remainder = out["is_mapped_leader"].eq(0)
    breeze_rank = out.loc[remainder].groupby("win_market_id")["breeze_score"].rank(ascending=False, method="first")
    out["is_mapped_breeze"] = 0
    out.loc[breeze_rank.index, "is_mapped_breeze"] = breeze_rank.eq(1).astype(int)
    sit_score = out["trail_rate_prior"].fillna(0) + np.where(
        out["front_row"].eq(1) & out["barrier"].eq(1) & out["is_mapped_leader"].eq(0),
        0.4,
        0.0,
    )
    out["sit_score"] = sit_score
    sit_rank = out.loc[out["is_mapped_leader"].eq(0) & out["is_mapped_breeze"].eq(0)].groupby("win_market_id")[
        "sit_score"
    ].rank(ascending=False, method="first")
    out["is_mapped_sit"] = 0
    out.loc[sit_rank.index, "is_mapped_sit"] = sit_rank.eq(1).astype(int)
    out["n_inside_draws"] = out.groupby("win_market_id")["inside_barrier"].transform("sum")
    out["leader_draw_contested"] = (out["n_inside_draws"] >= 2).astype(int)
    return out


def build_features(joined: pd.DataFrame | None = None) -> pd.DataFrame:
    frame = joined.copy() if joined is not None else load_joined()
    if frame.empty:
        return frame

    frame["meeting_date"] = pd.to_datetime(frame["meeting_date"]).dt.strftime("%Y-%m-%d")
    frame["won"] = (
        frame["win_result"].astype(str).str.upper().eq("WINNER")
        | frame["place"].fillna(0).eq(1)
    ).astype(int)
    frame["horse_key"] = frame["horse_name"].map(normalize_horse_name)
    frame["trainer_key"] = frame["trainer"].fillna("").str.lower().str.strip()
    frame["driver_key"] = frame["driver"].fillna("").str.lower().str.strip()
    frame["barrier"] = frame["row_and_barrier"].map(parse_barrier)
    frame["front_row"] = frame["row_and_barrier"].map(parse_front_row)
    frame["inside_barrier"] = frame["barrier"].le(2).astype(float)
    frame["wide_barrier"] = frame["barrier"].ge(6).astype(float)
    frame["inside_draw_score"] = [
        inside_draw_score(front, barrier)
        for front, barrier in zip(frame["front_row"], frame["barrier"])
    ]
    frame["field_size"] = frame.groupby(["win_market_id"])["horse_name"].transform("count")
    frame["distance"] = pd.to_numeric(frame["distance"], errors="coerce")
    frame["tab_number"] = pd.to_numeric(frame["tab_number"], errors="coerce")
    frame["place"] = pd.to_numeric(frame["place"], errors="coerce")
    frame["mile_rate"] = pd.to_numeric(frame.get("mile_rate"), errors="coerce")
    frame["last_half"] = pd.to_numeric(frame.get("third_quarter"), errors="coerce") + pd.to_numeric(
        frame.get("fourth_quarter"), errors="coerce"
    )
    frame["q4"] = pd.to_numeric(frame.get("fourth_quarter"), errors="coerce")
    frame["dist_band"] = frame["distance"].map(distance_band)
    frame["is_sprint"] = frame["dist_band"].eq(0).astype(float)
    frame["is_stay"] = frame["dist_band"].eq(2).astype(float)
    frame["is_pace"] = frame.get("race_type", pd.Series(index=frame.index)).astype(str).str.lower().str.contains("pace")
    frame["is_pace"] = frame["is_pace"].astype(float)
    frame["metro_grade"] = frame.get("win_market_name", pd.Series(index=frame.index)).map(parse_grade)
    track_key = frame["track_code"].fillna(frame.get("betfair_track"))
    frame["sprint_lane"] = track_key.map(track_sprint_lane)
    frame["metro_track"] = track_key.map(track_is_metro)
    flags = frame.get("stewards_comments", pd.Series(index=frame.index)).map(parse_stewards_flags)
    for flag in ("led", "death", "trail", "gate_speed", "three_wide", "used_lane", "held_up", "broke", "tyre"):
        frame[flag] = flags.map(lambda item, name=flag: item.get(name, 0)).astype(int)

    frame = add_entity_history(frame, "horse_key", "horse")
    frame = add_entity_history(frame, "trainer_key", "trainer")
    frame = add_entity_history(frame, "driver_key", "driver")
    frame = add_shifted_history(
        frame,
        [
            "led",
            "death",
            "trail",
            "gate_speed",
            "three_wide",
            "used_lane",
            "held_up",
            "broke",
            "tyre",
            "distance",
            "mile_rate",
            "last_half",
            "q4",
            "metro_grade",
            "trainer_key",
            "driver_key",
        ],
    )
    frame["driver_changed"] = (
        frame["last_driver_key"].notna()
        & frame["driver_key"].ne("")
        & frame["last_driver_key"].ne(frame["driver_key"])
    ).astype(float)
    frame["trainer_changed"] = (
        frame["last_trainer_key"].notna()
        & frame["trainer_key"].ne("")
        & frame["last_trainer_key"].ne(frame["trainer_key"])
    ).astype(float)
    frame["dist_change"] = frame["distance"] - frame["last_distance"]
    frame["class_drop"] = frame["last_metro_grade"] - frame["metro_grade"]
    frame["forgive_last"] = (
        frame["last_place"].ge(6)
        & (
            frame["last_held_up"].fillna(0).eq(1)
            | frame["last_broke"].fillna(0).eq(1)
            | frame["last_tyre"].fillna(0).eq(1)
        )
    ).astype(float)
    frame["inside_with_sprint_lane"] = frame["inside_barrier"] * frame["sprint_lane"]
    frame["sit_with_sprint_lane"] = frame["trail_rate_prior"].fillna(0) * frame["sprint_lane"].fillna(0)
    frame = add_distance_form(frame)
    frame = add_speed_map(frame)
    frame = add_solonsch_ratings(frame)
    frame["nz_runner"] = frame["horse_name"].astype(str).str.contains(r"\bNZ\b", case=False, regex=True)
    frame["n_nz"] = frame.groupby("win_market_id")["nz_runner"].transform("sum")
    frame = frame.sort_values(["meeting_date", "win_market_id", "tab_number"], kind="mergesort")
    return frame


FEATURE_COLUMNS = [
    "horse_starts_prior",
    "horse_wins_prior",
    "horse_win_rate_prior",
    "horse_places_prior",
    "horse_avg_place_prior",
    "horse_starts_l5",
    "horse_wins_l5",
    "horse_places_l5",
    "horse_avg_place_l5",
    "days_since_last",
    "last_place",
    "trainer_starts_prior",
    "trainer_win_rate_prior",
    "driver_starts_prior",
    "driver_win_rate_prior",
    "driver_changed",
    "trainer_changed",
    "barrier",
    "front_row",
    "inside_barrier",
    "wide_barrier",
    "inside_draw_score",
    "tab_number",
    "field_size",
    "distance",
    "dist_band",
    "dist_change",
    "is_sprint",
    "is_stay",
    "is_pace",
    "same_dist_win_rate_prior",
    "metro_grade",
    "metro_track",
    "class_drop",
    "sprint_lane",
    "inside_with_sprint_lane",
    "sit_with_sprint_lane",
    "led_rate_prior",
    "death_rate_prior",
    "trail_rate_prior",
    "gate_speed_rate_prior",
    "three_wide_rate_prior",
    "used_lane_rate_prior",
    "last_mile_rate",
    "last_last_half",
    "last_q4",
    "lead_score",
    "breeze_score",
    "is_mapped_leader",
    "is_mapped_breeze",
    "is_mapped_sit",
    "n_inside_draws",
    "leader_draw_contested",
    "forgive_last",
    "speed_rating",
    "speed_gap",
    "speed_discard",
    "speed_soft_discard",
    "speed_rank",
]


def write_features(frame: pd.DataFrame | None = None) -> pd.DataFrame:
    features = build_features(frame)
    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    features.to_csv(config.FEATURES_PATH, index=False)
    print(f"Wrote {len(features):,} feature rows to {config.FEATURES_PATH}")
    return features


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build pre-race form features")
    parser.parse_args(argv)
    write_features()
