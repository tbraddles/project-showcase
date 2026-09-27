"""Place-market efficiency and Harville(win BSP) vs PLACE_BSP."""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.betting import back_profit, brier_score
from common.harville import harville_place_probs

AU_STATES = frozenset({"QLD", "NSW", "VIC", "WA", "SA", "TAS", "NT", "ACT"})


def placed_flag(place_result: pd.Series) -> pd.Series:
    return place_result.astype(str).str.upper().eq("WINNER").astype(int)


def add_harville(frame: pd.DataFrame) -> pd.DataFrame:
    """Race-normalise 1/WIN_BSP and convert to Harville place probabilities."""
    out = frame.copy().reset_index(drop=True)
    out["win_implied_raw"] = 1.0 / out["win_bsp"]
    totals = out.groupby("win_market_id")["win_implied_raw"].transform("sum")
    out["win_p"] = np.where(totals > 0, out["win_implied_raw"] / totals, np.nan)
    n_places = out.groupby("win_market_id")["placed"].transform("sum").clip(lower=2, upper=3)
    out["n_places"] = n_places.astype(int)

    harville = np.full(len(out), np.nan)
    for market_id, group in out.groupby("win_market_id"):
        probs = harville_place_probs(group["win_p"].to_numpy(), int(group["n_places"].iloc[0]))
        harville[group.index] = probs
    out["harville_p"] = harville
    out["place_implied"] = 1.0 / out["place_bsp"]
    return out


def _odds_band(bsp: float) -> str:
    if bsp < 1.5:
        return "1.01-1.50"
    if bsp < 2.5:
        return "1.50-2.50"
    if bsp < 4:
        return "2.50-4.00"
    if bsp < 8:
        return "4.00-8.00"
    return "8.00+"


def build_place_report(frame: pd.DataFrame, sport_label: str = "harness") -> str:
    data = frame.dropna(subset=["place_bsp", "win_bsp", "placed"]).copy()
    data = data.loc[
        np.isfinite(data["place_bsp"])
        & np.isfinite(data["win_bsp"])
        & data["place_bsp"].gt(1)
        & data["place_bsp"].le(50)
        & data["win_bsp"].gt(1)
        & data["win_bsp"].le(200)
    ]
    if data.empty:
        return f"No {sport_label} rows with both WIN_BSP and PLACE_BSP.\n"

    data = add_harville(data)
    data = data.dropna(subset=["harville_p", "place_implied"])
    place_overround = (
        data.groupby("win_market_id")["place_implied"].sum().replace([np.inf, -np.inf], np.nan).dropna()
    )
    data["place_band"] = data["place_bsp"].map(_odds_band)
    band = (
        data.groupby("place_band")
        .agg(
            runners=("placed", "size"),
            place_rate=("placed", "mean"),
            mean_place_implied=("place_implied", "mean"),
            mean_harville=("harville_p", "mean"),
        )
        .reindex(["1.01-1.50", "1.50-2.50", "2.50-4.00", "4.00-8.00", "8.00+"])
    )
    band["gap_bsp"] = band["place_rate"] - band["mean_place_implied"]
    band["gap_harville"] = band["place_rate"] - band["mean_harville"]

    overlay = data["harville_p"] > data["place_implied"]
    selected = data.loc[overlay].copy()
    if selected.empty:
        overlay_roi = float("nan")
        overlay_n = 0
        overlay_profit = 0.0
    else:
        pnl = [
            back_profit(bool(won), float(odds), 1.0)
            for won, odds in zip(selected["placed"], selected["place_bsp"])
        ]
        overlay_profit = float(np.sum(pnl))
        overlay_n = int(len(selected))
        overlay_roi = overlay_profit / overlay_n

    lines = [
        f"PuntBot place vs win-BSP (Australian {sport_label})",
        "",
        "Win probabilities are race-normalised 1/WIN_BSP. Harville converts those to P(place).",
        "No form model. One pre-declared book: $1 place when Harville > 1/PLACE_BSP.",
        "",
        f"Runners with place BSP: {len(data):,}",
        f"Markets: {data['win_market_id'].nunique():,}",
        f"Mean sum of 1/PLACE_BSP per race: {place_overround.mean():.3f} "
        f"(about n_places if the place book is tight)",
        f"Place rate: {data['placed'].mean():.3f}  mean 1/PLACE_BSP: {data['place_implied'].mean():.3f}  "
        f"mean Harville: {data['harville_p'].mean():.3f}",
        f"Brier 1/PLACE_BSP: {brier_score(data['place_implied'], data['placed']):.4f}",
        f"Brier Harville(win BSP): {brier_score(data['harville_p'], data['placed']):.4f}",
        f"Mean Harville minus 1/PLACE_BSP: {(data['harville_p'] - data['place_implied']).mean():+.4f}",
        "",
        "Place rate vs implied by PLACE_BSP band:",
    ]
    for name, row in band.dropna(how="all").iterrows():
        lines.append(
            f"  {name}: n={int(row['runners']):,}  place={row['place_rate']:.3f}  "
            f"1/bsp={row['mean_place_implied']:.3f} ({row['gap_bsp']:+.3f})  "
            f"harville={row['mean_harville']:.3f} ({row['gap_harville']:+.3f})"
        )
    roi_txt = "n/a" if np.isnan(overlay_roi) else f"{overlay_roi:.1%}"
    lines.extend(
        [
            "",
            f"Harville overlay place backs: {overlay_n:,} bets  profit={overlay_profit:+.2f}  ROI={roi_txt}",
            "(6% commission, $1 stake. Full sample, not a holdout.)",
        ]
    )
    if overlay_n:
        selected = selected.copy()
        selected["place_band"] = selected["place_bsp"].map(_odds_band)
        selected["pnl"] = [
            back_profit(bool(won), float(odds), 1.0)
            for won, odds in zip(selected["placed"], selected["place_bsp"])
        ]
        lines.append("Overlay by PLACE_BSP band (this is where any plus comes from):")
        by_band = selected.groupby("place_band")["pnl"].agg(["size", "sum", "mean"])
        for name, row in by_band.reindex(["1.01-1.50", "1.50-2.50", "2.50-4.00", "4.00-8.00", "8.00+"]).dropna(how="all").iterrows():
            lines.append(
                f"  {name}: n={int(row['size']):,}  profit={row['sum']:+.1f}  roi={row['mean']:.1%}"
            )
    lines.extend(
        [
            "",
            "PLACE_BSP is the better probability (lower Brier than Harville).",
            "Harville overrates short-priced placers and underrates long ones (usual independence bias).",
            "A plus on the overlay book that lives in 8+ place shots is the longshot trap again, not a licence to bet.",
        ]
    )
    return "\n".join(lines) + "\n"
