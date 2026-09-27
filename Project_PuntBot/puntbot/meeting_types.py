"""Pre-declared meeting-type slices. Report every slice, not the winners."""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

import config
from puntbot.backtest import back_profit
from puntbot.calibration import BSP_HI, BSP_LO, brier_score
from puntbot.experiments import _prepare, frozen_candidate_mask

MEETING_TYPES_PATH = config.OUTPUT_DIR / "meeting_types_report.txt"
MIN_BAND = 150
MIN_FROZEN = 60


def _gait(row: pd.Series) -> str:
    text = str(row.get("race_type") or "").strip().title()
    if text == "Pace":
        return "Pace"
    if text == "Trot":
        return "Trot"
    return "Other"


def _grade(row: pd.Series) -> str:
    value = row.get("metro_grade")
    if pd.isna(value):
        return "Unknown grade"
    return "Metro grade (M)" if float(value) >= 0.5 else "Provincial grade (S)"


def _dist(row: pd.Series) -> str:
    band = row.get("dist_band")
    if pd.isna(band):
        return "Unknown distance"
    if float(band) <= 0:
        return "Sprint (<=1760m)"
    if float(band) <= 1:
        return "Mid (1761-2300m)"
    return "Stay (>2300m)"


def _venue_class(row: pd.Series) -> str:
    value = row.get("metro_track")
    if pd.isna(value):
        return "Unknown venue class"
    return "Metro venue" if float(value) >= 0.5 else "Provincial venue"


def assign_slices(frame: pd.DataFrame) -> list[tuple[str, str, pd.Series]]:
    """Return (family, label, mask) for every pre-declared meeting type."""
    gait = frame.apply(_gait, axis=1)
    grade = frame.apply(_grade, axis=1)
    dist = frame.apply(_dist, axis=1)
    venue = frame.apply(_venue_class, axis=1)
    track = frame["track_code"].fillna("?").astype(str)

    slices: list[tuple[str, str, pd.Series]] = [
        ("all", "All holdout runners", pd.Series(True, index=frame.index)),
        ("gait", "Pace", gait.eq("Pace")),
        ("gait", "Trot", gait.eq("Trot")),
        ("grade", "Metro grade (M)", grade.eq("Metro grade (M)")),
        ("grade", "Provincial grade (S)", grade.eq("Provincial grade (S)")),
        ("venue", "Metro venue", venue.eq("Metro venue")),
        ("venue", "Provincial venue", venue.eq("Provincial venue")),
        ("distance", "Sprint (<=1760m)", dist.eq("Sprint (<=1760m)")),
        ("distance", "Mid (1761-2300m)", dist.eq("Mid (1761-2300m)")),
        ("distance", "Stay (>2300m)", dist.eq("Stay (>2300m)")),
    ]
    for code in sorted(track.unique()):
        slices.append(("track", f"Track {code}", track.eq(code)))
    for code in sorted(track.unique()):
        slices.append(("track_gait", f"{code} Pace", track.eq(code) & gait.eq("Pace")))
        slices.append(("track_gait", f"{code} Trot", track.eq(code) & gait.eq("Trot")))
    return slices


def _frozen_pnl(frame: pd.DataFrame) -> tuple[int, float, float, float]:
    selected = frame.loc[frozen_candidate_mask(frame)]
    if selected.empty:
        return 0, float("nan"), 0.0, float("nan")
    pnl = [
        back_profit(bool(won), float(odds), 1.0)
        for won, odds in zip(selected["won"], selected["win_bsp"])
    ]
    profit = float(np.sum(pnl))
    n = int(len(selected))
    return n, float(selected["won"].mean()), profit, profit / n


def _band_stats(frame: pd.DataFrame) -> dict[str, float]:
    band = frame.loc[frame["win_bsp"].between(BSP_LO, BSP_HI)]
    if band.empty:
        return {
            "band_n": 0,
            "actual": float("nan"),
            "model_p": float("nan"),
            "implied": float("nan"),
            "brier_model": float("nan"),
            "brier_bsp": float("nan"),
        }
    won = band["won"].astype(float)
    return {
        "band_n": int(len(band)),
        "actual": float(won.mean()),
        "model_p": float(band["model_p"].mean()),
        "implied": float((1.0 / band["win_bsp"]).mean()),
        "brier_model": brier_score(band["model_p"], won),
        "brier_bsp": brier_score(1.0 / band["win_bsp"], won),
    }


def summarise_slice(frame: pd.DataFrame, family: str, label: str) -> dict[str, object]:
    stats = _band_stats(frame)
    frozen_n, strike, profit, roi = _frozen_pnl(frame)
    model_better = (
        stats["band_n"] >= MIN_BAND
        and not np.isnan(stats["brier_model"])
        and stats["brier_model"] < stats["brier_bsp"]
    )
    return {
        "family": family,
        "slice": label,
        **stats,
        "frozen_n": frozen_n,
        "frozen_strike": strike,
        "frozen_profit": profit,
        "frozen_roi": roi,
        "model_beats_bsp": model_better,
    }


def run_meeting_types(frame: pd.DataFrame) -> pd.DataFrame:
    data = _prepare(frame)
    data["year"] = pd.to_datetime(data["meeting_date"]).dt.year
    rows = []
    for family, label, mask in assign_slices(data):
        subset = data.loc[mask]
        if subset.empty:
            continue
        row = summarise_slice(subset, family, label)
        if row["band_n"] < MIN_BAND and row["frozen_n"] < MIN_FROZEN:
            continue
        rows.append(row)
        for year, year_frame in subset.groupby("year"):
            year_row = summarise_slice(year_frame, f"{family}|year", f"{label} {int(year)}")
            if year_row["band_n"] >= MIN_BAND or year_row["frozen_n"] >= MIN_FROZEN:
                rows.append(year_row)
    return pd.DataFrame(rows)


def write_report(results: pd.DataFrame) -> str:
    lines = [
        "PuntBot meeting-type slices (research only)",
        "",
        "Pre-declared: gait, metro/provincial grade, venue class, distance, track, track+gait.",
        "Every slice that clears the sample floor is listed. Do not promote a winner.",
        f"Band = BSP {BSP_LO:.2f}-{BSP_HI:.0f}. model_beats_bsp = Brier_model < Brier_BSP and n>={MIN_BAND}.",
        "Frozen ROI is the locked rule only, $1 stake, 6% commission.",
        "",
        (
            f"{'slice':<28} {'band_n':>7} {'act':>6} {'1/bsp':>6} {'model':>6} "
            f"{'BrM':>6} {'BrB':>6} {'better':>6} {'frz':>5} {'roi':>7}"
        ),
        "-" * 96,
    ]
    for row in results.itertuples(index=False):
        if "|year" in str(row.family):
            continue
        better = "yes" if row.model_beats_bsp else "no"
        roi = "    n/a" if pd.isna(row.frozen_roi) else f"{row.frozen_roi:7.1%}"
        lines.append(
            f"{str(row.slice)[:28]:<28} {int(row.band_n):7d} "
            f"{row.actual:6.3f} {row.implied:6.3f} {row.model_p:6.3f} "
            f"{row.brier_model:6.3f} {row.brier_bsp:6.3f} {better:>6} "
            f"{int(row.frozen_n):5d} {roi}"
        )

    beats = results.loc[~results["family"].astype(str).str.contains("|year", regex=False) & results["model_beats_bsp"]]
    lines.extend(["", "Slices where the model Brier-beats BSP on the $2.50-8 band:"])
    if beats.empty:
        lines.append("  none")
    else:
        for row in beats.itertuples(index=False):
            lines.append(f"  {row.slice} (band_n={int(row.band_n)})")

    lines.extend(
        [
            "",
            "Year splits (same slices) are in output/meeting_types_detail.csv.",
            "A slice needs model_beats_bsp in both 2025 and 2026 before it is a lead.",
            "",
        ]
    )
    text = "\n".join(lines)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MEETING_TYPES_PATH.write_text(text + "\n", encoding="utf-8")
    results.to_csv(config.OUTPUT_DIR / "meeting_types_detail.csv", index=False)
    print(text)
    return text


def load_holdouts() -> pd.DataFrame:
    parts = []
    for year in (2025, 2026):
        path = config.DATA_PROCESSED_DIR / f"predictions_holdout_{year}.csv"
        if path.exists():
            parts.append(pd.read_csv(path))
    if not parts:
        raise SystemExit("Missing holdout prediction files. Run 07_calibrate.py first.")
    return pd.concat(parts, ignore_index=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Slice holdouts by meeting type")
    parser.parse_args(argv)
    write_report(run_meeting_types(load_holdouts()))


if __name__ == "__main__":
    main()
