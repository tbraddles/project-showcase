# Greyhound research

Prices first. There is no form scrape and no live betting.

```
cd Project_PuntBot/greyhound
..\venv\Scripts\python 01_ingest_betfair.py
```

Reads the public Aus/NZ Greyhound Hub files (2020–Aug 2026) and writes `output/bsp_baseline.txt`.

If win rates already match `1/BSP` in every band, stop. Do not build a form model on an efficient market.

They do. See `Findings.md`. Gaps are ~0 in every BSP band. Overround is 1.003.
