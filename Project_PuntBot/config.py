"""Paths and research defaults for the PuntBot pipeline."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent

DATA_DIR = ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
BETFAIR_RAW_DIR = DATA_RAW_DIR / "betfair"
DATA_PROCESSED_DIR = DATA_DIR / "processed"
DATA_REFERENCE_DIR = DATA_DIR / "reference"
OUTPUT_DIR = ROOT / "output"
DATABASE_DIR = ROOT / "Database"

DB_PATH = DATABASE_DIR / "race_results.db"
TRACK_CODES_PATH = DATA_REFERENCE_DIR / "track_codes.csv"

FEATURES_PATH = DATA_PROCESSED_DIR / "features.csv"
PREDICTIONS_PATH = DATA_PROCESSED_DIR / "predictions.csv"
JOIN_REPORT_PATH = OUTPUT_DIR / "join_report.txt"
BASELINE_REPORT_PATH = OUTPUT_DIR / "bsp_baseline.txt"
BACKTEST_REPORT_PATH = OUTPUT_DIR / "backtest_report.txt"
EQUITY_CURVE_PATH = OUTPUT_DIR / "equity_curve.csv"

BETFAIR_ASSETS_BASE = "https://betfair-datascientists.github.io/data/assets"
BETFAIR_YEARS = (2020, 2021, 2022, 2023, 2024, 2025)
BETFAIR_MONTHLY_YEAR = 2026
BETFAIR_MONTHLY_THROUGH = 8

HARNESS_FIELDS_BASE = "https://natsite.harness.org.au/racing/fields/race-fields/?mc="
HARNESS_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/192.168.1.5 Safari/537.36"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
}

# Major Australian meeting codes used for bulk form scraping.
MAJOR_TRACK_CODES = (
    "GP",
    "MX",
    "PC",
    "AP",
    "RE",
    "NC",
    "GD",
    "HO",
    "LA",
    "BU",
    "GE",
    "BE",
    "BH",
    "PN",
)

AU_STATE_CODES = frozenset({"QLD", "NSW", "VIC", "WA", "SA", "TAS", "NT", "ACT"})

COMMISSION = 0.06
MIN_EDGE = 0.10
MIN_BSP = 1.50
MAX_BSP = 20.0
MIN_PREPLAY_VOLUME = 200.0
FLAT_STAKE = 1.0
KELLY_FRACTION = 0.25

WALK_FORWARD_MIN_TRAIN_MONTHS = 3
RANDOM_SEED = 42
