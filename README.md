# Watchlist

A web-hosted watchlist: tracks companies you're not currently invested in,
pulls market cap / LTM P/E / most-recent-quarter EPS growth from Yahoo
Finance weekly, and flags two things automatically:

- **Growth surprise** — actual EPS growth (most recent quarter, YoY) vs the
  long-term growth target you set per company. A beat of more than 5
  percentage points flags `POSITIVE` (worth more research time); a miss of
  more than 5 points flags `NEGATIVE` (worth a thesis check). Anything
  closer than that is `IN_LINE`.
- **Momentum** — split into two independent signals:
  - *Trend*: price vs 50-day/200-day SMA, golden/death cross.
  - *Acceleration*: trailing 3-month price return vs the prior 3-month
    return — is the rate of change itself speeding up or slowing down
    (`ACCELERATING` / `DECELERATING` / `FLAT`).

The published page shows the table AND a watchlist editor — add, remove, or
retarget a company's expected growth rate. Edits commit directly to
`watchlist.json` via the GitHub Contents API, called from the page's own
JS. No second workflow needed; next week's run picks up whatever is in
`watchlist.json` at trigger time.

## How it runs

```
GitHub Actions cron (Monday mornings, UTC)
  -> scripts/generate_watchlist.py
       -> load watchlist.json
       -> pull market cap / LTM P/E / quarterly EPS growth / 1y daily prices
          per ticker from Yahoo Finance (yfinance, threaded, no API key)
       -> compute growth-surprise flag + trend/acceleration momentum flags
       -> write history/<date>.json
       -> render site/index.html
  -> commit watchlist.json / history/ / site/index.html back to main
  -> deploy site/ to GitHub Pages
```

No LLM calls, no API keys, no repo secrets — this app is pure structured
data from Yahoo Finance.

## Local dev

```bash
pip install -r requirements.txt
python scripts/generate_watchlist.py
```

Edit `watchlist.json` directly to add a test company before running, e.g.:

```json
[{"tk": "NVDA", "co": "Nvidia", "ex": "NASDAQ", "expected_eps_growth_pct": 20}]
```

Open `site/index.html` in a browser to check the render.

## One-time setup

1. In this repo's Settings → Pages, set **Source** to "GitHub Actions".
2. Run the workflow once manually (Actions tab → Watchlist → Run workflow)
   to confirm the full pipeline before trusting the weekly schedule.

The watchlist editor prompts once for a GitHub fine-grained Personal Access
Token, scoped only to this repo with `Contents: read/write` permission —
nothing broader. It's stored in the browser's `localStorage` only, never
sent anywhere except `api.github.com`.

## Known limitations (v1, intentional)

- Valuation is LTM P/E only — no P/B, EV/EBITDA, or other multiples yet.
- EPS growth "actual" is most-recent-quarter YoY, which can be noisy for
  seasonal or lumpy businesses — no TTM smoothing.
- Repo is public by default (free GitHub Pages requires it unless you have
  GitHub Pro/Team). Nothing secret lives in code, but the watchlist and its
  growth targets are visible to anyone with the link.
- If yfinance's `earningsQuarterlyGrowth` or `trailingPE` is missing for a
  ticker (thin coverage, recent IPO, etc.), that field renders as `—` and
  the growth flag is `UNKNOWN` rather than guessed.
