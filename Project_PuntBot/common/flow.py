"""Preplay steam vs BSP. Came-in means the price shortened into the off."""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.betting import back_profit, brier_score

MOVE_THRESHOLD = 0.05


def classify_move(preplay: pd.Series, bsp: pd.Series, threshold: float = MOVE_THRESHOLD) -> pd.Series:
    """Came-in: preplay odds longer than BSP. Drifted: preplay shorter than BSP."""
    ratio = preplay / bsp
    out = pd.Series("stable", index=preplay.index, dtype=object)
    out = out.mask(ratio >= 1.0 + threshold, "came_in")
    out = out.mask(ratio <= 1.0 / (1.0 + threshold), "drifted")
    return out


def _bucket_stats(frame: pd.DataFrame, label: str) -> dict[str, float]:
    if frame.empty:
        return {
            "slice": label,
            "n": 0,
            "win_rate": float("nan"),
            "implied": float("nan"),
            "gap": float("nan"),
            "brier_bsp": float("nan"),
            "profit_bsp": 0.0,
            "roi_bsp": float("nan"),
        }
    won = frame["won"].astype(float)
    implied = 1.0 / frame["win_bsp"]
    pnl = [
        back_profit(bool(w), float(o), 1.0)
        for w, o in zip(frame["won"], frame["win_bsp"])
    ]
    profit = float(np.sum(pnl))
    n = int(len(frame))
    return {
        "slice": label,
        "n": n,
        "win_rate": float(won.mean()),
        "implied": float(implied.mean()),
        "gap": float(won.mean() - implied.mean()),
        "brier_bsp": brier_score(implied, won),
        "profit_bsp": profit,
        "roi_bsp": profit / n,
    }


def build_flow_report(frame: pd.DataFrame, price_col: str = "win_preplay_ltp") -> str:
    data = frame.dropna(subset=[price_col, "win_bsp", "won"]).copy()
    data = data.loc[
        np.isfinite(data[price_col])
        & np.isfinite(data["win_bsp"])
        & data[price_col].gt(1)
        & data[price_col].le(200)
        & data["win_bsp"].gt(1)
        & data["win_bsp"].le(200)
    ]
    if data.empty:
        return "No rows with a preplay traded price and BSP.\n"

    data["move"] = classify_move(data[price_col], data["win_bsp"])
    rows = [
        _bucket_stats(data, "all with preplay price"),
        _bucket_stats(data.loc[data["move"].eq("came_in")], "came in (preplay >= BSP + 5%)"),
        _bucket_stats(data.loc[data["move"].eq("drifted")], "drifted (preplay <= BSP - 5%)"),
        _bucket_stats(data.loc[data["move"].eq("stable")], "stable (move < 5%)"),
    ]
    if "win_preplay_volume" in data.columns:
        liquid = data.loc[data["win_preplay_volume"].fillna(0).ge(200)]
        rows.extend(
            [
                _bucket_stats(liquid.loc[liquid["move"].eq("came_in")], "came in, volume >= 200"),
                _bucket_stats(liquid.loc[liquid["move"].eq("drifted")], "drifted, volume >= 200"),
            ]
        )

    lines = [
        "PuntBot preplay flow vs BSP (Australian harness)",
        "",
        f"Move uses {price_col} vs WIN_BSP. Came-in = market shortened at least 5%.",
        "Gap = actual win rate minus mean 1/BSP. Books are $1 backs at BSP, 6% commission.",
        "Full sample, not a holdout. Following steam at BSP is the test, not a strategy grid.",
        "",
        f"{'slice':<36} {'n':>9} {'win':>6} {'1/bsp':>6} {'gap':>7} {'roi@bsp':>8}",
        "-" * 80,
    ]
    for row in rows:
        roi = "    n/a" if np.isnan(row["roi_bsp"]) else f"{row['roi_bsp']:8.1%}"
        gap = "    n/a" if np.isnan(row["gap"]) else f"{row['gap']:+7.3f}"
        win = "   n/a" if np.isnan(row["win_rate"]) else f"{row['win_rate']:6.3f}"
        imp = "   n/a" if np.isnan(row["implied"]) else f"{row['implied']:6.3f}"
        lines.append(
            f"{row['slice']:<36} {int(row['n']):9d} {win} {imp} {gap} {roi}"
        )
    lines.extend(
        [
            "",
            "If came-in gap is ~0, late money is already in BSP. Following it at BSP should lose after commission.",
            "A leftover-steam story needs came-in horses to win more than 1/BSP.",
        ]
    )
    for move, title in (("came_in", "Came-in by BSP band"), ("drifted", "Drifted by BSP band")):
        part = data.loc[data["move"].eq(move)].copy()
        if part.empty:
            continue
        part["band"] = pd.cut(
            part["win_bsp"],
            bins=[1, 2, 5, 10, 20, 200],
            labels=["1-2", "2-5", "5-10", "10-20", "20+"],
            include_lowest=True,
        )
        lines.extend(["", title + ":"])
        for name, group in part.groupby("band", observed=True):
            stats = _bucket_stats(group, str(name))
            lines.append(
                f"  {name}: n={stats['n']:,}  win={stats['win_rate']:.3f}  "
                f"1/bsp={stats['implied']:.3f}  gap={stats['gap']:+.3f}  roi@bsp={stats['roi_bsp']:.1%}"
            )
    return "\n".join(lines) + "\n"
