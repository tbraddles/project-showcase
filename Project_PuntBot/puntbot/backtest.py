"""BSP backtest with commission, filters, and simple baselines."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import config


def break_even_probability(odds: float, commission: float = config.COMMISSION) -> float:
    net_odds = 1.0 + (odds - 1.0) * (1.0 - commission)
    return 1.0 / net_odds


def back_profit(won: bool, odds: float, stake: float, commission: float = config.COMMISSION) -> float:
    if won:
        return (odds - 1.0) * (1.0 - commission) * stake
    return -stake


def kelly_fraction(prob: float, odds: float, commission: float = config.COMMISSION) -> float:
    b = (odds - 1.0) * (1.0 - commission)
    if b <= 0:
        return 0.0
    fraction = (prob * (b + 1.0) - 1.0) / b
    return max(0.0, float(fraction))


def apply_filters(
    frame: pd.DataFrame,
    min_edge: float = config.MIN_EDGE,
    min_bsp: float = config.MIN_BSP,
    max_bsp: float = config.MAX_BSP,
    min_volume: float = config.MIN_PREPLAY_VOLUME,
) -> pd.DataFrame:
    out = frame.copy()
    out["be_p"] = out["win_bsp"].map(lambda odds: break_even_probability(odds))
    out["edge"] = out["model_p"] / out["be_p"] - 1.0
    mask = (
        out["edge"].ge(min_edge)
        & out["win_bsp"].between(min_bsp, max_bsp)
        & out["win_preplay_volume"].fillna(0).ge(min_volume)
        & out["model_p"].gt(0)
    )
    return out.loc[mask].copy()


def _summarise(bets: pd.DataFrame, label: str, stake_col: str) -> dict[str, float]:
    if bets.empty:
        return {
            "strategy": label,
            "bets": 0,
            "strike": float("nan"),
            "profit": 0.0,
            "roi": float("nan"),
            "max_dd": 0.0,
            "staked": 0.0,
        }
    profit = bets[stake_col]
    equity = profit.cumsum()
    drawdown = equity - equity.cummax()
    staked = bets["stake"].sum() if "stake" in bets.columns else float(len(bets))
    return {
        "strategy": label,
        "bets": int(len(bets)),
        "strike": float(bets["won"].mean()),
        "profit": float(profit.sum()),
        "roi": float(profit.sum() / staked) if staked else float("nan"),
        "max_dd": float(drawdown.min()) if not drawdown.empty else 0.0,
        "staked": float(staked),
    }


def _odds_band(bsp: float) -> str:
    if bsp < 2:
        return "1.50-2.00"
    if bsp < 5:
        return "2.00-5.00"
    if bsp < 10:
        return "5.00-10.00"
    return "10.00-20.00"


def run_backtest(predictions: pd.DataFrame | None = None) -> dict[str, dict[str, float]]:
    frame = predictions.copy() if predictions is not None else pd.read_csv(config.PREDICTIONS_PATH)
    if frame.empty:
        raise SystemExit("No predictions found. Run 04_train.py first.")
    frame["won"] = (
        frame["won"].astype(int)
        if "won" in frame.columns
        else frame["win_result"].astype(str).str.upper().eq("WINNER").astype(int)
    )
    frame["meeting_date"] = pd.to_datetime(frame["meeting_date"])
    frame = frame.sort_values(["meeting_date", "win_market_id", "tab_number"])

    selected = apply_filters(frame)
    selected["stake"] = config.FLAT_STAKE
    selected["flat_profit"] = [
        back_profit(bool(won), float(odds), config.FLAT_STAKE)
        for won, odds in zip(selected["won"], selected["win_bsp"])
    ]
    selected["kelly_frac"] = [
        min(1.0, kelly_fraction(float(prob), float(odds)) * config.KELLY_FRACTION)
        for prob, odds in zip(selected["model_p"], selected["win_bsp"])
    ]
    selected["kelly_stake"] = selected["kelly_frac"]
    selected["kelly_profit"] = [
        back_profit(bool(won), float(odds), float(stake))
        for won, odds, stake in zip(selected["won"], selected["win_bsp"], selected["kelly_stake"])
    ]

    favorites = (
        frame.sort_values(["win_market_id", "win_bsp"])
        .groupby("win_market_id", as_index=False)
        .first()
        .copy()
    )
    favorites["stake"] = config.FLAT_STAKE
    favorites["flat_profit"] = [
        back_profit(bool(won), float(odds), config.FLAT_STAKE)
        for won, odds in zip(favorites["won"], favorites["win_bsp"])
    ]

    summaries = {
        "model_flat": _summarise(selected.rename(columns={"flat_profit": "pnl"}), "model_flat", "pnl"),
        "model_kelly": _summarise(
            selected.rename(columns={"kelly_profit": "pnl"}).assign(stake=selected["kelly_stake"]),
            "model_kelly",
            "pnl",
        ),
        "always_favorite": _summarise(favorites.rename(columns={"flat_profit": "pnl"}), "always_favorite", "pnl"),
    }

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not selected.empty:
        equity = selected[["meeting_date", "track_code", "horse_name", "win_bsp", "model_p", "edge", "won", "flat_profit"]].copy()
        equity["equity"] = equity["flat_profit"].cumsum()
        equity.to_csv(config.EQUITY_CURVE_PATH, index=False)

    report = _format_report(frame, selected, summaries)
    config.BACKTEST_REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    return summaries


def _format_report(frame: pd.DataFrame, selected: pd.DataFrame, summaries: dict[str, dict[str, float]]) -> str:
    lines = [
        "PuntBot BSP backtest",
        "",
        f"Out-of-sample runners: {len(frame):,}",
        f"Markets: {frame['win_market_id'].nunique():,}",
        f"Date range: {frame['meeting_date'].min().date()} to {frame['meeting_date'].max().date()}",
        f"Commission: {config.COMMISSION:.0%}",
        f"Filters: edge>={config.MIN_EDGE:.0%}, BSP {config.MIN_BSP}-{config.MAX_BSP}, "
        f"min preplay volume {config.MIN_PREPLAY_VOLUME:.0f}",
        "",
        "Strategy results (unit stake unless noted):",
    ]
    for row in summaries.values():
        lines.append(
            f"  {row['strategy']}: bets={row['bets']:,}  strike={row['strike']:.3f}  "
            f"profit={row['profit']:+.2f}  roi={row['roi']:.1%}  maxDD={row['max_dd']:.2f}"
        )

    if not selected.empty:
        selected = selected.copy()
        selected["odds_band"] = selected["win_bsp"].map(_odds_band)
        lines.extend(["", "Model flat-stake by BSP band:"])
        band = selected.groupby("odds_band").agg(bets=("won", "size"), strike=("won", "mean"), profit=("flat_profit", "sum"))
        for name, row in band.iterrows():
            lines.append(f"  {name}: n={int(row['bets'])}  strike={row['strike']:.3f}  profit={row['profit']:+.2f}")

        if "track_code" in selected.columns:
            lines.extend(["", "Model flat-stake by track:"])
            by_track = (
                selected.groupby("track_code")
                .agg(bets=("won", "size"), profit=("flat_profit", "sum"))
                .sort_values("bets", ascending=False)
                .head(12)
            )
            for name, row in by_track.iterrows():
                lines.append(f"  {name}: n={int(row['bets'])}  profit={row['profit']:+.2f}")

        if "meeting_date" in selected.columns:
            selected["year"] = selected["meeting_date"].dt.year
            lines.extend(["", "Model flat-stake by year:"])
            by_year = selected.groupby("year").agg(bets=("won", "size"), profit=("flat_profit", "sum"))
            for year, row in by_year.iterrows():
                lines.append(f"  {int(year)}: n={int(row['bets'])}  profit={row['profit']:+.2f}")

    lines.extend(
        [
            "",
            "This is a research backtest of BSP bets, not live trading.",
            "A positive paper ROI is necessary but not sufficient to bet real money.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Backtest model selections at BSP")
    parser.add_argument("--predictions", type=Path, default=None, help="Optional predictions CSV")
    args = parser.parse_args(argv)
    preds = pd.read_csv(args.predictions) if args.predictions else None
    run_backtest(preds)
