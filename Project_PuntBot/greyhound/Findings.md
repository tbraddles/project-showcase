# Greyhound findings so far

Research only. Australian win markets, Betfair Starting Price, no commission in this report.

## BSP baseline (2020–Aug 2026)

- **2,181,100** AU runners, **302,280** races
- Mean overround **1.003**
- Favourite strike **42.2%**
- Brier of `1/BSP` **0.098**
- Median preplay volume **$616** (thinner than the harness books we filtered)

Win rate vs implied, every band:

| BSP | n | win | 1/BSP | gap |
| --- | ---: | ---: | ---: | ---: |
| 1.01–2.00 | 78,156 | 0.611 | 0.613 | −0.002 |
| 2.00–5.00 | 456,028 | 0.305 | 0.305 | 0.000 |
| 5.00–10.00 | 463,636 | 0.145 | 0.145 | 0.000 |
| 10.00–20.00 | 434,030 | 0.074 | 0.074 | 0.000 |
| 20.00+ | 749,250 | 0.023 | 0.023 | 0.000 |

This market is as tight as harness, or tighter. There is no drunk odds band to attack with a form model at BSP.

## What not to do next

Do not scrape The Dogs / GRV form to beat BSP. That is the harness result again. If we continue greyhounds it has to be a different question (live price vs BSP, places, something other than “form vs starting price”).
