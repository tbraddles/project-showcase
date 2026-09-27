# PuntBot findings so far

This is a research note, not a betting recommendation. All “profit” numbers are paper BSP results after 6% commission.

## Locked rule

**`frozen_candidate`**: backs only, $1 stake, one model top pick per race, BSP $2.50–$8, Solonsch cull, min volume. Other experiment rows are not the strategy.

## Calibration (the diagnostic that matters)

On the $2.50–$8 band, **BSP is the better probability**. Form-only `model_p` is not.

All runners in that band (2025 + 2026 holdouts, 15,686 horses):

- They win **22.3%**. Mean `1/BSP` is **22.0%**. Mean `model_p` is **15.0%**.
- Brier: model **0.181** vs BSP **0.167**.
- The model under-rates most $2.50–$8 horses (it leaves probability on longshots) and over-rates the ones it likes most (`model_p` 0.30+ wins less often than claimed).

`frozen_candidate` looks calibrated **on average** (mean `model_p` 24.5% vs strike 24.4% vs `1/BSP` 24.6%). That is not an edge. A fair price after 6% commission should lose about 5%. It does.

Same story every year and every core track. BSP’s gap to actual is ~0. The model’s gap on the whole band is about +7 pp of missed win rate.

## Holdout P&L once 2025 is a full year

Jan–Jul 2025 Betfair dates were dropped by a parser bug. The old **+5.1%** was **August–December only** (853 bets). With the missing months restored:

| | 2025 (full) | 2026 (Jan–Aug) | Pooled |
| --- | ---: | ---: | ---: |
| Bets | 2,018 | 1,274 | 3,292 |
| Strike | 24.7% | 23.9% | 24.4% |
| Paper ROI | **−3.8%** | **−6.5%** | **−4.9%** |

2025 was never a working year. It was a five-month slice. 2026 matched the market and lost after commission.

## Meeting types

Pre-declared slices on the same holdouts: gait, metro vs provincial grade, venue class, distance, track, track+gait. Full table: `output/meeting_types_report.txt`.

**The model does not Brier-beat BSP in any slice.** Pace, trots, metro, provincial, sprint, stay, all five tracks.

Frozen-rule paper ROI by type (do not treat these as a menu):

- Trots **−12%**, provincial grade **−15%**, stays **−43%** (small)
- Sprints about flat (**−0.4%**)
- Melton pace **+10%** (254 bets) — still a worse probability than BSP, and 2026 is only 91 bets at +2.8%
- Albion Park pace **+3.5%** — same problem: BSP is still the better price

A few tracks can print a plus after commission by variance. None of them is a better forecast than the market.

## Could this be a betting model now?

**No.** Meeting type does not create an edge the model already failed to price. Do not promote Melton pace. Do not add live orders.

Full tables: `output/calibration_report.txt`, `output/meeting_types_report.txt`.
