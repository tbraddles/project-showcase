# PuntBot agent brief

Read this before changing code or launching more scrapes. It is the packed
context from the research chat. Keep it current when a decision changes.

## Mission

Research-only EV pipeline for Australian harness racing. Form answers
P(win). Betfair BSP is the opponent. No live orders, no API betting.

A positive paper ROI is a lead, not a licence to bet.

## Hard rules

- Research only. Do not add order placement.
- Honesty over optimism. The market is efficient (BSP overround ≈ 1).
- Do not hunt more experiment filters. The +14% figures were mined on
  one Oct–Dec 2024 quarter.
- Lays are diagnostics, never a bankroll story. ROI is profit / capital
  at risk. Backs: $1 stake. Lays: $1 liability.
- Use `Project_PuntBot/venv` for Python (system Python breaks pandas).
- Scrape via `natsite.harness.org.au`. `www.harness.org.au` is Cloudflare 403.
- Melton code is `MX` (not ME). Menangle is `PC` (not MB).
- Run commands from `Project_PuntBot` so `config.py` paths resolve.

## Locked product decision

Frozen candidate (backs only):

1. One horse per race (model top pick, or Solonsch top pick if that is the rater).
2. BSP between $2.50 and $8.
3. Solonsch as a cull (“must be fast enough”) or as the rater.
4. No lays in the strategy.

Do not treat `lay_model_longshot_edges` (~+1.8% on unit liability) as a win.

## Data state (after calibration)

- Form 2023–Aug 2026, five tracks. **161,421** runners, 99.6% joined.
- In the $2.50–$8 band, BSP Brier beats `model_p`. Mean model_p is 15%
  vs 22% actual / 22% 1/BSP. The model is not a better price than the market.
- Full-year 2025 `frozen_candidate` is **−3.8%** (2,018 bets), not the old
  Aug–Dec +5.1%. 2026 is **−6.5%**. Pooled **−4.9%**.
- Do not hunt a replacement rule.

## What already failed / worked (same thin quarter)

Failed: every-edge backs, mapped-leader-only, metro-only, kitchen-sink features
without a price-band filter.

Paper-positive on that quarter only: BSP $2.50–$8, one pick/race, Solonsch
probs. These will shrink on a real holdout.

## Pipeline

```
python 01_ingest_betfair.py
python 02_scrape_form.py --start YYYY-MM-DD --end YYYY-MM-DD --tracks GP,MX,PC,AP,RE --from-betfair
python 03_join.py
python 04_train.py
python 05_backtest.py
python 06_experiments.py --no-rebuild
pytest
```

`--from-betfair` only visits date/track pairs already in `betfair_runners`.
Skip-existing is on by default.

## Current workstreams

### A. Form history — done for core tracks

2023–2025 scrape finished for `GP,MX,PC,AP,RE`. 1,076 jobs, 86,850 new
horse rows this run, 24 HTTP 500 skips. Join is 99.5%.

### B. Freeze the candidate — done

`frozen_candidate` is in `puntbot/experiments.py`: model top pick, BSP
$2.50–$8, Solonsch cull, min volume. No 10% edge filter. On the old
Oct–Dec 2024 quarter it is about **+1.3%** — much lower than the mined
+14% rows, which is the honest locked number.

### C. 2025 holdout — done

`frozen_candidate` survived 2025 at **+5.1%** (853 bets). Unfiltered
still loses. Do not promote other 2025-positive rows.

### D. Second unseen year — done

### E. Calibration — done

`model_p` is a worse probability than BSP in the $2.50–$8 band.
`frozen_candidate` is calibrated to the market and loses after commission.
Do not hunt a replacement rule.

## File map

- `config.py` — paths, commission 0.06, scrape headers, major codes
- `puntbot/scrape_form.py` — HTTP scrape (default), Playwright optional
- `puntbot/join.py` — date + venue + TAB, `CODE_ALIASES` for ME/MX
- `puntbot/features.py` — form-only features, Solonsch ratings
- `puntbot/model.py` — walk-forward GBM, race-normalised probs
- `puntbot/backtest.py` — BSP backs, commission, Kelly
- `puntbot/experiments.py` — selective tests; lays are unit-liability
- `Findings.md` — human findings
- `Theory.md` / `Considerations.md` — source notes (may be stubs)
- `data/reference/track_codes.csv` — MX=Melton, PC=Menangle
- `Database/race_results.db` — gitignored SQLite

## Subagent report format

When you finish, return this block to the parent (and write it to
`output/agent_<task>_status.txt` if you can):

```
TASK:
CHANGED:
TESTS:
BLOCKERS:
NEXT:
```

Do not commit unless the user asked. Do not push.
