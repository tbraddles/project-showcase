"""Selective-betting experiments aimed at lifting paper ROI.

The default backtest loses on 10-20 shots. These tests try the opposite of
"bet every model edge": cull slow horses (Solonsch), bet fewer races, and
in one case lay horses the speed ratings say cannot win.
"""

from __future__ import annotations

import argparse
import numpy as np
import pandas as pd

import config
from puntbot.backtest import back_profit, break_even_probability
from puntbot.model import run_train

EXPERIMENTS_PATH = config.OUTPUT_DIR / "experiments_report.txt"


def lay_profit(won: bool, odds: float, liability: float = 1.0, commission: float = config.COMMISSION) -> float:
    """Unit-liability lay: risk $1 if the horse wins, so ROI matches capital at risk."""
    if odds <= 1.0:
        return 0.0
    if won:
        return -liability
    return liability / (odds - 1.0) * (1.0 - commission)


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["won"] = out["won"].astype(int)
    out["meeting_date"] = pd.to_datetime(out["meeting_date"])
    if "be_p" not in out.columns:
        out["be_p"] = out["win_bsp"].map(lambda odds: break_even_probability(float(odds)))
    if "edge" not in out.columns:
        out["edge"] = out["model_p"] / out["be_p"] - 1.0
    if "solonsch_p" in out.columns:
        out["solonsch_edge"] = out["solonsch_p"] / out["be_p"] - 1.0
    if "model_rank" not in out.columns:
        out["model_rank"] = out.groupby("win_market_id")["model_p"].rank(ascending=False, method="first")
    if "implied_p" not in out.columns:
        raw = 1.0 / out["win_bsp"]
        out["implied_p"] = raw / out.groupby("win_market_id")[raw.name].transform("sum")
    out["shrunk_p"] = 0.55 * out["model_p"] + 0.45 * out["implied_p"]
    out["shrunk_edge"] = out["shrunk_p"] / out["be_p"] - 1.0
    return out


def _summarise(bets: pd.DataFrame, label: str) -> dict[str, float | str]:
    if bets.empty:
        return {"strategy": label, "bets": 0, "markets": 0, "strike": float("nan"), "profit": 0.0, "roi": float("nan")}
    profit = bets["pnl"]
    staked = bets["stake"].sum()
    return {
        "strategy": label,
        "bets": int(len(bets)),
        "markets": int(bets["win_market_id"].nunique()),
        "strike": float(bets["won"].mean()),
        "profit": float(profit.sum()),
        "roi": float(profit.sum() / staked) if staked else float("nan"),
    }


def _backs(frame: pd.DataFrame, mask: pd.Series, label: str, prob_col: str = "model_p") -> dict[str, float | str]:
    selected = frame.loc[mask].copy()
    if selected.empty:
        return _summarise(selected, label)
    selected["stake"] = 1.0
    selected["pnl"] = [
        back_profit(bool(won), float(odds), 1.0)
        for won, odds in zip(selected["won"], selected["win_bsp"])
    ]
    return _summarise(selected, label)


def _lays(frame: pd.DataFrame, mask: pd.Series, label: str) -> dict[str, float | str]:
    selected = frame.loc[mask].copy()
    if selected.empty:
        return _summarise(selected, label)
    selected["stake"] = 1.0  # $1 liability, comparable to a $1 back
    selected["pnl"] = [
        lay_profit(bool(won), float(odds), 1.0)
        for won, odds in zip(selected["won"], selected["win_bsp"])
    ]
    return _summarise(selected, label)


def default_edge_mask(frame: pd.DataFrame, min_edge: float = config.MIN_EDGE) -> pd.Series:
    return (
        frame["edge"].ge(min_edge)
        & frame["win_bsp"].between(config.MIN_BSP, config.MAX_BSP)
        & frame["win_preplay_volume"].fillna(0).ge(config.MIN_PREPLAY_VOLUME)
    )


def frozen_candidate_mask(frame: pd.DataFrame) -> pd.Series:
    """Locked research rule: one model top pick per race, BSP 2.50-8, Solonsch cull, min volume."""
    speed_ok = frame.get("speed_discard", pd.Series(0, index=frame.index)).fillna(0).eq(0)
    has_rating = frame.get("speed_rating", pd.Series(np.nan, index=frame.index)).notna()
    return (
        frame["model_rank"].eq(1)
        & frame["win_bsp"].between(2.5, 8.0)
        & speed_ok
        & has_rating
        & frame["win_preplay_volume"].fillna(0).ge(config.MIN_PREPLAY_VOLUME)
    )


def run_experiments(frame: pd.DataFrame) -> pd.DataFrame:
    data = _prepare(frame)
    base = default_edge_mask(data)
    pace = data.get("is_pace", pd.Series(1, index=data.index)).fillna(1).eq(1)
    metro = data.get("metro_track", pd.Series(0, index=data.index)).fillna(0).eq(1)
    front = data.get("front_row", pd.Series(np.nan, index=data.index)).eq(1)
    speed_ok = data.get("speed_discard", pd.Series(0, index=data.index)).fillna(0).eq(0)
    speed_soft_ok = data.get("speed_soft_discard", pd.Series(0, index=data.index)).fillna(0).eq(0)
    has_rating = data.get("speed_rating", pd.Series(np.nan, index=data.index)).notna()
    few_nz = data.get("n_nz", pd.Series(0, index=data.index)).fillna(0).le(1)
    leader = data.get("is_mapped_leader", pd.Series(0, index=data.index)).fillna(0).eq(1)
    sit = data.get("is_mapped_sit", pd.Series(0, index=data.index)).fillna(0).eq(1)
    top_speed = data.get("speed_rank", pd.Series(99, index=data.index)).fillna(99).le(3)
    top_model = data["model_rank"].le(2)
    solonsch_edge = data.get("solonsch_edge", pd.Series(np.nan, index=data.index)).ge(0.10)

    rows = [
        _backs(data, frozen_candidate_mask(data), "frozen_candidate"),
        _backs(data, base, "current_every_edge"),
        _backs(data, base & data["win_bsp"].le(8), "no_longshots_bsp_le_8"),
        _backs(data, base & data["win_bsp"].between(2.5, 8), "sweet_spot_2.5_8"),
        _backs(data, base & data["model_rank"].eq(1), "top_model_pick_only"),
        _backs(data, base & data["model_rank"].eq(1) & speed_ok & has_rating, "top_pick_and_speed_ok"),
        _backs(data, base & speed_ok & speed_soft_ok & has_rating, "solonsch_cull"),
        _backs(data, base & top_model & top_speed & speed_ok, "overlay_model_and_speed"),
        _backs(data, solonsch_edge & speed_ok & has_rating & data["win_bsp"].between(1.5, 8), "solonsch_probs_only"),
        _backs(data, base & leader, "mapped_leader_only"),
        _backs(data, base & (leader | sit) & data["win_bsp"].le(8), "leader_or_sit_short_odds"),
        _backs(data, base & pace, "pace_only_skip_trots"),
        _backs(data, base & metro & pace, "metro_pace_only"),
        _backs(data, base & front & data["win_bsp"].le(8), "front_row_short_odds"),
        _backs(data, base & few_nz & pace, "avoid_nz_and_trots"),
        _backs(data, data["shrunk_edge"].ge(0.10) & data["win_bsp"].between(1.5, 8) & speed_ok, "shrunk_p_plus_cull"),
        _backs(
            data,
            data["model_rank"].eq(1)
            & data["speed_rank"].eq(1)
            & data["win_bsp"].between(1.8, 6)
            & data["win_preplay_volume"].fillna(0).ge(config.MIN_PREPLAY_VOLUME),
            "fastest_and_model_favourite",
        ),
        _lays(
            data,
            data.get("speed_discard", pd.Series(0, index=data.index)).eq(1)
            & data["win_bsp"].between(4, 12)
            & data["win_preplay_volume"].fillna(0).ge(config.MIN_PREPLAY_VOLUME)
            & has_rating,
            "lay_solonsch_discards_4_12",
        ),
        _lays(
            data,
            base & data["win_bsp"].ge(10) & data["model_rank"].ge(4),
            "lay_model_longshot_edges",
        ),
    ]
    return pd.DataFrame(rows).sort_values(["roi", "profit"], ascending=False)


def write_report(results: pd.DataFrame, frame: pd.DataFrame | None = None) -> str:
    split_note = "These are hypothesis tests on the same out-of-sample predictions."
    if frame is not None and "split" in frame.columns:
        splits = sorted({str(value) for value in frame["split"].dropna().unique()})
        if splits and all(str(value).startswith("holdout") for value in splits):
            split_note = (
                f"Calendar holdout only ({', '.join(splits)}). "
                "Train years are excluded. Do not promote non-frozen rows from this table."
            )
    lines = [
        "PuntBot selective-betting experiments",
        "",
        "Strike = how often the horse won (not how often the bet won, if you are laying).",
        "Lay P&L is unit liability: risk $1 if the horse wins. Do not treat long-odds lays as a bankroll strategy.",
        "",
        split_note,
        "A better paper ROI here is a lead, not a licence to bet live.",
        "",
        f"{'strategy':<32} {'bets':>6} {'mkts':>6} {'strike':>7} {'profit':>9} {'roi':>8}",
        "-" * 74,
    ]
    for row in results.itertuples(index=False):
        strike = "   n/a" if pd.isna(row.strike) else f"{row.strike:7.3f}"
        roi = "    n/a" if pd.isna(row.roi) else f"{row.roi:8.1%}"
        lines.append(
            f"{row.strategy:<32} {int(row.bets):6d} {int(row.markets):6d} "
            f"{strike} {row.profit:+9.2f} {roi}"
        )
    lines.extend(
        [
            "",
            "Reading the tests:",
            "- frozen_candidate is the locked research rule (one model top pick, BSP 2.50-8, Solonsch cull, min volume).",
            "- Other rows are historical hypotheses. Do not switch the locked rule because one of them printed well.",
            "- current_every_edge is the default 10-20-heavy backtest.",
            "- no_longshots / sweet_spot ask whether the model is only useful in the 2.5-8 band.",
            "- solonsch_cull throws out horses more than 1.8s slower than the race's best half-mile rating.",
            "- overlay requires the model and the speed ratings to like the same horse.",
            "- lay rows are diagnostics only, sized to $1 liability. They are not a bankroll strategy.",
        ]
    )
    text = "\n".join(lines) + "\n"
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EXPERIMENTS_PATH.write_text(text, encoding="utf-8")
    print(text)
    return text


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run selective-betting ROI experiments")
    parser.add_argument("--no-rebuild", action="store_true", help="Reuse existing predictions.csv")
    parser.add_argument(
        "--holdout-year",
        type=int,
        nargs="?",
        const=config.HOLDOUT_YEAR,
        default=None,
        metavar="YEAR",
        help=(
            f"Rebuild predictions with calendar-year holdout (default {config.HOLDOUT_YEAR} "
            "when flag is given without a year). Ignored with --no-rebuild."
        ),
    )
    args = parser.parse_args(argv)
    if args.no_rebuild:
        frame = pd.read_csv(config.PREDICTIONS_PATH)
    else:
        frame = run_train(rebuild_features=True, holdout_year=args.holdout_year)
    write_report(run_experiments(frame), frame)
