# Project PuntBot

Research pipeline for Australian harness racing. It estimates win probabilities from official form, compares them to Betfair Starting Price, and backtests whether any edge survives commission.

This is not a live betting bot. There is no order placement.

## What this is

Form data answers "how likely is this horse to win?" Betfair prices answer "what will the market pay?" Expected value is the difference. The pipeline keeps those two things separate:

1. Download historical Betfair win-market files (BSP, volume, results).
2. Scrape race-level form and results from harness.org.au.
3. Join them on date, venue, and TAB number (name matching is the fallback).
4. Train a form-only model so the market is the opponent, not an input.
5. Backtest BSP bets with commission, edge, odds, and liquidity filters.

A positive paper ROI is a research result, not a reason to bet real money.

## Setup

```
git clone https://github.com/tbraddles/project-showcase.git
cd project-showcase/Project_PuntBot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

Run every command from `Project_PuntBot` so `config.py` resolves local paths.

## Pipeline

**1. Betfair market data and a no-model baseline**

```
python 01_ingest_betfair.py
```

Downloads the free Aus/NZ Harness files published by [Betfair's Automation Hub](https://betfair-datascientists.github.io/data/dataListing/), loads Australian win-market rows into SQLite, and writes `output/bsp_baseline.txt`.

**2. Form and results**

```
python 02_scrape_form.py --start 2025-01-01 --end 2025-03-31 --tracks GP,MX,PC,AP --from-betfair
```

Scrapes official meeting pages via `natsite.harness.org.au` (the www host is Cloudflare-protected). Skips days already stored and upserts `races` / `horse_results`. `--from-betfair` only visits date/track pairs that already exist in the Betfair table. `--browser` uses Playwright if you need it. `puntbot_scraper.py` is a thin wrapper around the same command.

**3. Join**

```
python 03_join.py
```

Writes `runner_matches` and `output/join_report.txt`. Unmatched runners are reported, not dropped silently.

**4. Features and model**

```
python 04_train.py
```

Builds pre-race form features (no BSP / last-traded price) and trains a walk-forward `HistGradientBoostingClassifier`. Probabilities are renormalised so they sum to 1 inside each race. Output: `data/processed/predictions.csv`.

**5. Backtest**

```
python 05_backtest.py
```

Simulates BSP backs with 6% commission, a 10% edge filter, BSP between 1.50 and 20, and a minimum preplay volume. Reports flat-stake and fractional-Kelly results against an always-back-the-favorite baseline in `output/backtest_report.txt`.

## Layout

- `puntbot/` — ingest, scrape, join, features, model, backtest
- `01_ingest_betfair.py` … `05_backtest.py` — thin CLI wrappers
- `data/reference/track_codes.csv` — meeting code to Betfair venue names
- `Database/race_results.db` — local SQLite (gitignored)
- `data/raw/betfair/` — downloaded Hub files (gitignored)
- `output/` — reports (gitignored)

## Betfair account

Not required for this research build. The Hub CSVs are public. An API key is only needed if you later add live market reads or order placement, which this repo does not do.

## Example research run

After ingesting Hub files for 2020–2026 and scraping H2 2024 form for Albion Park, Gloucester Park, Redcliffe, Melton (`MX`), and Menangle (`PC`):

- Betfair AU win rows: 551,104. Mean BSP overround ≈ 1.00. Favorite strike rate 42.9%.
- Form-to-market join: 21,852 / 21,955 runners (99.5%), mostly via date + venue + TAB number.
- Walk-forward model on Oct–Dec 2024: 9,077 out-of-sample runners, 976 markets.
- BSP backtest (6% commission, 10% edge, BSP 1.50–20, min volume 200): model flat-stake ROI **−14.4%** vs always-back-the-favorite **−6.6%**.

That is the point of the pipeline. The market looks efficient in this sample. Do not add live betting on the back of a losing paper result.

## Tests

```
pytest
```
