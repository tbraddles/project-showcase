"""Reliability of form-only model_p versus actual wins and versus BSP.

This is a diagnostic. It does not propose bets.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

import config
from puntbot.experiments import _prepare, frozen_candidate_mask
from puntbot.model import holdout_year_predict

CALIBRATION_PATH = config.CALIBRATION_REPORT_PATH
HOLDOUT_YEARS = (2025, 2026)
P_BINS = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.55)
BSP_LO, BSP_HI = 2.5, 8.0


def brier_score(prob: pd.Series, won: pd.Series) -> float:
    return float(np.mean((prob.to_numpy(dtype=float) - won.to_numpy(dtype=float)) ** 2))


def expected_calibration_error(prob: pd.Series, won: pd.Series, bins: tuple[float, ...] = P_BINS) -> float:
    table = reliability_table(prob, won, bins)
    if table.empty:
        return float("nan")
    weight = table["n"] / table["n"].sum()
    return float((weight * (table["actual"] - table["mean_p"]).abs()).sum())


def reliability_table(
    prob: pd.Series,
    won: pd.Series,
    bins: tuple[float, ...] = P_BINS,
) -> pd.DataFrame:
    frame = pd.DataFrame({"p": pd.to_numeric(prob, errors="coerce"), "won": won.astype(float)})
    frame = frame.dropna(subset=["p"])
    if frame.empty:
        return pd.DataFrame(columns=["bin", "n", "mean_p", "actual", "gap"])
    labels = [f"{bins[i]:.2f}-{bins[i + 1]:.2f}" for i in range(len(bins) - 1)]
    frame["bin"] = pd.cut(frame["p"], bins=bins, labels=labels, include_lowest=True, right=False)
    grouped = frame.dropna(subset=["bin"]).groupby("bin", observed=True)
    rows = []
    for label, group in grouped:
        if group.empty:
            continue
        mean_p = float(group["p"].mean())
        actual = float(group["won"].mean())
        rows.append(
            {
                "bin": str(label),
                "n": int(len(group)),
                "mean_p": mean_p,
                "actual": actual,
                "gap": actual - mean_p,
            }
        )
    return pd.DataFrame(rows)


def _short_odds(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[frame["win_bsp"].between(BSP_LO, BSP_HI)].copy()


def _format_table(table: pd.DataFrame, columns: list[str]) -> list[str]:
    if table.empty:
        return ["  (none)"]
    header = "  " + " ".join(f"{col:>10}" for col in columns)
    lines = [header]
    for row in table.itertuples(index=False):
        cells = []
        for col in columns:
            value = getattr(row, col)
            if col in {"n", "bets"}:
                cells.append(f"{int(value):>10d}")
            elif isinstance(value, float):
                cells.append(f"{value:>10.3f}")
            else:
                cells.append(f"{str(value):>10}")
        lines.append("  " + " ".join(cells))
    return lines


def _slice_summary(frame: pd.DataFrame, label: str) -> list[str]:
    if frame.empty:
        return [f"{label}: no rows", ""]
    won = frame["won"].astype(float)
    model = frame["model_p"]
    implied = 1.0 / frame["win_bsp"]
    lines = [
        label,
        (
            f"  n={len(frame)}  mean_model_p={model.mean():.3f}  "
            f"actual={won.mean():.3f}  gap={won.mean() - model.mean():+.3f}"
        ),
        (
            f"  mean_1/BSP={implied.mean():.3f}  "
            f"Brier_model={brier_score(model, won):.4f}  "
            f"Brier_BSP={brier_score(implied, won):.4f}  "
            f"ECE={expected_calibration_error(model, won):.3f}"
        ),
        "  reliability (model_p bins):",
    ]
    table = reliability_table(model, won)
    lines.extend(_format_table(table, ["bin", "n", "mean_p", "actual", "gap"]))
    lines.append("")
    return lines


def _group_gaps(frame: pd.DataFrame, key: str) -> pd.DataFrame:
    rows = []
    for name, group in frame.groupby(key, dropna=False):
        if group.empty:
            continue
        actual = float(group["won"].mean())
        model = float(group["model_p"].mean())
        implied = float((1.0 / group["win_bsp"]).mean())
        rows.append(
            {
                key: str(name),
                "n": int(len(group)),
                "mean_p": model,
                "implied": implied,
                "actual": actual,
                "gap_model": actual - model,
                "gap_bsp": actual - implied,
            }
        )
    return pd.DataFrame(rows)


def build_report(frame: pd.DataFrame) -> str:
    data = _prepare(frame)
    data["year"] = pd.to_datetime(data["meeting_date"]).dt.year
    band = _short_odds(data)
    frozen = data.loc[frozen_candidate_mask(data)].copy()
    frozen["year"] = pd.to_datetime(frozen["meeting_date"]).dt.year

    lines = [
        "PuntBot calibration (research only - not a betting rule)",
        "",
        "Question: does model_p match win rate in the $2.50-$8 band?",
        "If Brier_model > Brier_BSP, the market is the better probability.",
        "gap = actual win rate minus mean predicted probability.",
        "",
    ]
    lines.extend(_slice_summary(band, f"All runners BSP {BSP_LO:.2f}-{BSP_HI:.0f}"))
    lines.extend(_slice_summary(frozen, "frozen_candidate only"))

    if not band.empty:
        lines.append("All runners $2.50-$8 by year:")
        lines.extend(_format_table(_group_gaps(band, "year"), ["year", "n", "mean_p", "implied", "actual", "gap_model", "gap_bsp"]))
        lines.append("")
        track_col = "track_code" if "track_code" in band.columns else None
        if track_col:
            lines.append("All runners $2.50-$8 by track:")
            lines.extend(
                _format_table(_group_gaps(band, track_col), [track_col, "n", "mean_p", "implied", "actual", "gap_model", "gap_bsp"])
            )
            lines.append("")

    if not frozen.empty:
        lines.append("frozen_candidate by year:")
        lines.extend(
            _format_table(_group_gaps(frozen, "year"), ["year", "n", "mean_p", "implied", "actual", "gap_model", "gap_bsp"])
        )
        lines.append("")
        if "track_code" in frozen.columns:
            lines.append("frozen_candidate by track:")
            lines.extend(
                _format_table(
                    _group_gaps(frozen, "track_code"),
                    ["track_code", "n", "mean_p", "implied", "actual", "gap_model", "gap_bsp"],
                )
            )
            lines.append("")

    return "\n".join(lines) + "\n"


def load_holdout_predictions(years: tuple[int, ...] = HOLDOUT_YEARS) -> pd.DataFrame:
    features = pd.read_csv(config.FEATURES_PATH)
    parts = []
    for year in years:
        predicted = holdout_year_predict(features, year)
        if predicted.empty:
            continue
        path = config.DATA_PROCESSED_DIR / f"predictions_holdout_{year}.csv"
        predicted.to_csv(path, index=False)
        print(f"Wrote {len(predicted):,} holdout_{year} rows to {path}")
        parts.append(predicted)
    if not parts:
        raise SystemExit("No holdout predictions. Rebuild features first.")
    return pd.concat(parts, ignore_index=True)


def write_report(frame: pd.DataFrame) -> str:
    text = build_report(frame)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CALIBRATION_PATH.write_text(text, encoding="utf-8")
    print(text)
    return text


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Calibrate model_p vs wins on holdout years")
    parser.add_argument(
        "--from-predictions",
        action="store_true",
        help="Use existing predictions.csv only (single split)",
    )
    args = parser.parse_args(argv)
    frame = pd.read_csv(config.PREDICTIONS_PATH) if args.from_predictions else load_holdout_predictions()
    write_report(frame)


if __name__ == "__main__":
    main()
