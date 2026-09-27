"""BSP efficiency report shared by harness and greyhound."""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.betting import brier_score

AU_STATES = frozenset({"QLD", "NSW", "VIC", "WA", "SA", "TAS", "NT", "ACT"})


def _odds_band(bsp: float) -> str:
    if bsp < 2:
        return "1.01-2.00"
    if bsp < 5:
        return "2.00-5.00"
    if bsp < 10:
        return "5.00-10.00"
    if bsp < 20:
        return "10.00-20.00"
    return "20.00+"


def build_baseline_text(frame: pd.DataFrame, sport_label: str) -> str:
    if frame.empty:
        return f"No Australian Betfair win rows with a BSP were found ({sport_label}).\n"

    market_overround = (
        frame.groupby("win_market_id")["implied"].sum().replace([np.inf, -np.inf], np.nan).dropna()
    )
    favorites = (
        frame.sort_values(["win_market_id", "win_bsp"])
        .groupby("win_market_id", as_index=False)
        .first()
    )
    frame = frame.copy()
    frame["odds_band"] = frame["win_bsp"].map(_odds_band)
    band = (
        frame.groupby("odds_band")
        .agg(
            runners=("won", "size"),
            win_rate=("won", "mean"),
            mean_implied=("implied", "mean"),
            mean_bsp=("win_bsp", "mean"),
        )
        .reindex(["1.01-2.00", "2.00-5.00", "5.00-10.00", "10.00-20.00", "20.00+"])
    )
    band["gap"] = band["win_rate"] - band["mean_implied"]

    by_track = (
        frame.groupby("track")
        .agg(
            runners=("won", "size"),
            markets=("win_market_id", "nunique"),
            median_preplay_vol=("win_preplay_volume", "median"),
            median_bsp_vol=("win_bsp_volume", "median"),
        )
        .sort_values("markets", ascending=False)
        .head(15)
    )

    lines = [
        f"PuntBot BSP efficiency baseline (Australian {sport_label} win markets)",
        "",
        f"Runners: {len(frame):,}",
        f"Markets: {frame['win_market_id'].nunique():,}",
        f"Meetings: {frame.groupby(['meeting_date', 'track']).ngroups:,}",
        f"Date range: {frame['meeting_date'].min()} to {frame['meeting_date'].max()}",
        f"Mean market overround (sum of 1/BSP): {market_overround.mean():.3f}",
        f"Favorite strike rate: {favorites['won'].mean():.3f}",
        f"Brier of 1/BSP: {brier_score(frame['implied'], frame['won']):.4f}",
        f"Median preplay volume: {frame['win_preplay_volume'].median():,.0f}",
        f"Median BSP volume: {frame['win_bsp_volume'].median():,.0f}",
        "",
        "Win rate vs implied probability by BSP band:",
    ]
    for band_name, row in band.dropna(how="all").iterrows():
        lines.append(
            f"  {band_name}: n={int(row['runners']):,}  win={row['win_rate']:.3f}  "
            f"implied={row['mean_implied']:.3f}  gap={row['gap']:+.3f}"
        )
    lines.extend(["", "Busiest tracks:"])
    for track, row in by_track.iterrows():
        lines.append(
            f"  {track}: {int(row['markets']):,} races, "
            f"median preplay vol {row['median_preplay_vol']:.0f}"
        )
    lines.extend(
        [
            "",
            "A positive gap means selections in that band win more often than 1/BSP.",
            "That is a market-bias observation, not a betting edge.",
            "If gaps are near zero and overround is ~1, form-vs-BSP is unlikely to pay.",
            "Commission is not applied in this report.",
        ]
    )
    return "\n".join(lines) + "\n"
