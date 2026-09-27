# Project PuntBot

Research-only Betfair work. No live orders.

```
Project_PuntBot/
  harness/      finished negative: form vs BSP on AU harness
  greyhound/    prices first — BSP baseline only
  common/       commission, Brier, Hub date parsing
  venv/
```

## Harness

Form-only win model vs Betfair Starting Price on five Australian tracks. **No edge.** The market is the better probability after commission. See `harness/Findings.md`.

```
cd harness
..\venv\Scripts\python -m pytest -q
```

## Greyhound

Do not scrape form yet. Ingest Hub prices and read the baseline.

```
cd greyhound
..\venv\Scripts\python 01_ingest_betfair.py
```

If win rates already match `1/BSP`, stop.
