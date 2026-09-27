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

## Place vs win BSP

Hub files already have `PLACE_BSP`. We converted race-normalised `1/WIN_BSP` to P(place) with Harville and compared that to the place market. No form model. Full AU sample 2020–Aug 2026, ~580k runners with a finite place price. Report: `output/place_vs_win_report.txt`.

**The place market is efficient.** Place rate equals mean `1/PLACE_BSP` (both 34.3%). Brier of place BSP **0.179** beats Harville **0.182**. Band gaps vs place BSP are about 0. Harville does the usual thing: too high on short placers, too low on long ones.

One pre-declared book — $1 place when Harville > `1/PLACE_BSP` — prints about **+3% to +4%** on the full sample. That plus is **place longshots** (4.00–8 about +15%, 8+ about +47%). Short place prices **lose** after commission (1.01–2.50 about −1% to −2%). Same trap as the win book. 2024 of that overlay was roughly flat. This is not a holdout and not a reason to bet places.

## Preplay flow vs BSP

Last traded before the off vs WIN_BSP. **Came-in** = shortened at least 5%. **Drifted** = lengthened at least 5%. Full AU sample, $1 at BSP, 6% commission. Report: `output/flow_vs_bsp_report.txt`.

Following steam at BSP **lost**. Came-in horses won **less** than `1/BSP` (gap about −1.0 to −1.5 pp, paper ROI about **−16% to −18%**). That is true in every odds band, including $2–$5.

Drifters won **more** than `1/BSP` (gap about +1.2 to +1.8 pp, paper ROI about **+7.5% to +8%**), also in every band — not only 20+ shots.

The money that came in overshot. BSP already includes the steam, then some. This is a full-sample lead, not a holdout, and fill is still assumed at BSP. Do not treat “back every drifter” as a funded system.

## Could this be a betting model now?

**Not from form or place.** Flow is the first structural lead: do not follow steam at BSP; drifters beat `1/BSP` on this full sample. That still needs a holdout and a real fill story before it is a system.

Full tables: `output/calibration_report.txt`, `output/meeting_types_report.txt`, `output/place_vs_win_report.txt`, `output/flow_vs_bsp_report.txt`.
