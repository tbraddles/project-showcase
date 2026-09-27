"""Pre-race form features. No Betfair prices are used as predictors."""

from __future__ import annotations

import argparse
import re

import numpy as np
import pandas as pd

import config
from puntbot.join import load_joined
from puntbot.names import normalize_horse_name


def parse_barrier(row_and_barrier: str | None) -> float:
    if row_and_barrier is None or (isinstance(row_and_barrier, float) and np.isnan(row_and_barrier)):
        return np.nan
    numbers = re.findall(r"\d+", str(row_and_barrier))
    if not numbers:
        return np.nan
    return float(numbers[-1])


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
    frame["field_size"] = frame.groupby(["win_market_id"])["horse_name"].transform("count")
    frame["distance"] = pd.to_numeric(frame["distance"], errors="coerce")
    frame["tab_number"] = pd.to_numeric(frame["tab_number"], errors="coerce")
    frame["place"] = pd.to_numeric(frame["place"], errors="coerce")

    frame = add_entity_history(frame, "horse_key", "horse")
    frame = add_entity_history(frame, "trainer_key", "trainer")
    frame = add_entity_history(frame, "driver_key", "driver")
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
    "barrier",
    "tab_number",
    "field_size",
    "distance",
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
