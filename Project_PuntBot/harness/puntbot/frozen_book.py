"""Diagnose the locked frozen_candidate book on holdout predictions."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

import config
from puntbot.backtest import back_profit
from puntbot.experiments import _prepare, frozen_candidate_mask

FROZEN_BOOK_PATH = config.OUTPUT_DIR / "frozen_book_2025.txt"
FROZEN_EQUITY_PATH = config.OUTPUT_DIR / "frozen_equity_2025.csv"


def select_frozen_bets(frame: pd.DataFrame) -> pd.DataFrame:
    """Return frozen_candidate rows with flat $1 stake and P&L."""
    data = _prepare(frame)
    selected = data.loc[frozen_candidate_mask(data)].copy()
    if selected.empty:
        selected["stake"] = pd.Series(dtype=float)
        selected["pnl"] = pd.Series(dtype=float)
        return selected
    selected = selected.sort_values(["meeting_date", "win_market_id"])
    selected["stake"] = 1.0
    selected["pnl"] = [
        back_profit(bool(won), float(odds), 1.0)
        for won, odds in zip(selected["won"], selected["win_bsp"])
    ]
    return selected


def max_drawdown(pnl: pd.Series) -> float:
    """Peak-to-trough equity drawdown (negative number)."""
    if pnl.empty:
        return 0.0
    equity = pnl.cumsum()
    return float((equity - equity.cummax()).min())


def equity_curve(bets: pd.DataFrame) -> pd.DataFrame:
    """Daily equity from chronological flat-stake P&L."""
    if bets.empty:
        return pd.DataFrame(columns=["date", "pnl", "equity"])
    daily = (
        bets.groupby("meeting_date", as_index=False)["pnl"]
        .sum()
        .rename(columns={"meeting_date": "date", "pnl": "pnl"})
    )
    daily["date"] = pd.to_datetime(daily["date"]).dt.date.astype(str)
    daily["equity"] = daily["pnl"].cumsum()
    return daily[["date", "pnl", "equity"]]


def _track_column(bets: pd.DataFrame) -> str:
    for col in ("track_code", "betfair_track", "track"):
        if col in bets.columns:
            return col
    raise KeyError("No track column found (expected track_code or betfair_track)")


def _overall_lines(bets: pd.DataFrame) -> list[str]:
    if bets.empty:
        return ["Overall: no frozen_candidate bets"]
    profit = float(bets["pnl"].sum())
    staked = float(bets["stake"].sum())
    roi = profit / staked if staked else float("nan")
    return [
        "Overall (flat $1 stake, 6% commission):",
        f"  bets={len(bets):,}  strike={bets['won'].mean():.3f}  "
        f"profit={profit:+.2f}  roi={roi:+.1%}  max_drawdown={max_drawdown(bets['pnl']):+.2f}",
    ]


def _monthly_lines(bets: pd.DataFrame) -> list[str]:
    if bets.empty:
        return ["Monthly: n/a"]
    monthly = bets.copy()
    monthly["month"] = monthly["meeting_date"].dt.to_period("M").astype(str)
    grouped = (
        monthly.groupby("month")
        .agg(bets=("won", "size"), strike=("won", "mean"), profit=("pnl", "sum"))
        .reset_index()
    )
    grouped["roi"] = grouped["profit"] / grouped["bets"]
    lines = ["", "Monthly:", f"  {'month':<8} {'bets':>6} {'strike':>7} {'profit':>9} {'roi':>8}"]
    for row in grouped.itertuples(index=False):
        lines.append(
            f"  {row.month:<8} {int(row.bets):6d} {row.strike:7.3f} "
            f"{row.profit:+9.2f} {row.roi:+8.1%}"
        )
    return lines


def _track_lines(bets: pd.DataFrame) -> list[str]:
    if bets.empty:
        return ["By track: n/a"]
    track_col = _track_column(bets)
    grouped = (
        bets.groupby(track_col)
        .agg(bets=("won", "size"), strike=("won", "mean"), profit=("pnl", "sum"))
        .sort_values("bets", ascending=False)
    )
    grouped["roi"] = grouped["profit"] / grouped["bets"]
    lines = ["", f"By track ({track_col}):", f"  {'track':<6} {'bets':>6} {'strike':>7} {'profit':>9} {'roi':>8}"]
    for name, row in grouped.iterrows():
        lines.append(
            f"  {str(name):<6} {int(row['bets']):6d} {row['strike']:7.3f} "
            f"{row['profit']:+9.2f} {row['roi']:+8.1%}"
        )
    return lines


def _liquidity_lines(bets: pd.DataFrame) -> list[str]:
    if bets.empty or "win_preplay_volume" not in bets.columns:
        return ["", "Liquidity: n/a"]
    vol = bets["win_preplay_volume"].fillna(0)
    n = len(bets)
    return [
        "",
        "Liquidity (win_preplay_volume):",
        f"  median={vol.median():.0f}  mean={vol.mean():.0f}",
        f"  share volume < 400: {(vol < 400).mean():.1%} ({int((vol < 400).sum())}/{n})",
        f"  share volume < 1000: {(vol < 1000).mean():.1%} ({int((vol < 1000).sum())}/{n})",
    ]


def _odds_lines(bets: pd.DataFrame) -> list[str]:
    if bets.empty:
        return ["", "Odds: n/a"]
    strike = float(bets["won"].mean())
    implied = 1.0 / bets["win_bsp"]
    return [
        "",
        "Odds:",
        f"  median BSP={bets['win_bsp'].median():.2f}",
        f"  strike={strike:.3f}  mean implied 1/BSP={implied.mean():.3f}  "
        f"strike minus implied={strike - implied.mean():+.3f}",
    ]


def build_report(bets: pd.DataFrame, split_label: str = "holdout_2025") -> str:
    lines = [
        "PuntBot frozen_candidate book diagnosis",
        "",
        f"Split: {split_label}",
        "Rule: one model top pick per race, BSP $2.50-$8, Solonsch cull, min preplay volume.",
        "Flat $1 stake, 6% commission. Research only — not a betting recommendation.",
        "",
        *_overall_lines(bets),
        *_monthly_lines(bets),
        *_track_lines(bets),
        *_liquidity_lines(bets),
        *_odds_lines(bets),
        "",
        "A positive paper ROI is a lead, not a licence to bet live.",
    ]
    return "\n".join(lines) + "\n"


def write_frozen_book(
    frame: pd.DataFrame,
    book_path: Path = FROZEN_BOOK_PATH,
    equity_path: Path = FROZEN_EQUITY_PATH,
) -> pd.DataFrame:
    """Select frozen bets and write diagnosis report + equity curve."""
    bets = select_frozen_bets(frame)
    split_label = "holdout_2025"
    if "split" in frame.columns:
        splits = sorted({str(v) for v in frame["split"].dropna().unique()})
        if splits:
            split_label = ", ".join(splits)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    book_path.write_text(build_report(bets, split_label=split_label), encoding="utf-8")
    equity_curve(bets).to_csv(equity_path, index=False)
    return bets


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Diagnose frozen_candidate book on holdout predictions")
    parser.add_argument(
        "--predictions",
        type=Path,
        default=config.PREDICTIONS_PATH,
        help="Predictions CSV (default: data/processed/predictions.csv)",
    )
    args = parser.parse_args(argv)
    frame = pd.read_csv(args.predictions)
    bets = write_frozen_book(frame)
    print(build_report(bets))
    print(f"Wrote {FROZEN_BOOK_PATH} and {FROZEN_EQUITY_PATH}")


if __name__ == "__main__":
    main()
