"""Paths for the greyhound research pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

SPORT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SPORT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DATA_DIR = SPORT_ROOT / "data"
BETFAIR_RAW_DIR = DATA_DIR / "raw" / "betfair"
OUTPUT_DIR = SPORT_ROOT / "output"
DATABASE_DIR = SPORT_ROOT / "Database"
DB_PATH = DATABASE_DIR / "greyhound_markets.db"
BASELINE_REPORT_PATH = OUTPUT_DIR / "bsp_baseline.txt"

BETFAIR_YEARS = (2020, 2021, 2022, 2023, 2024, 2025)
BETFAIR_MONTHLY_YEAR = 2026
BETFAIR_MONTHLY_THROUGH = 8
