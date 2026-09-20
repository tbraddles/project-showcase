# Sizzle Card

Brownlow night desk for the 2026 predicted 3-2-1. Built to live on a phone in the pub.

## Local

From `Project_Brownlow/web`:

```
npm install
python build_data.py
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Refresh the JSON after a new `05_predict.py` run with `python build_data.py`.

## Vercel

In the Vercel project, set **Root Directory** to `web`. Deploy. No extra env vars.

The app is a static Next.js client over `data/night.json` — the 2026 heatmap votes and per-game ranker scores.
