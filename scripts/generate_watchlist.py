#!/usr/bin/env python3
"""Watchlist orchestrator — entry point run by the GitHub Action.

Load watchlist -> pull Yahoo Finance data per ticker (threaded, no LLM) ->
compute growth-surprise + momentum flags -> write history -> render site.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yahoo_data import fetch  # noqa: E402
from momentum import compute_momentum  # noqa: E402
from render import render_site  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_FILE = ROOT / "watchlist.json"
HISTORY_DIR = ROOT / "history"

MAX_WORKERS = 5
GROWTH_SURPRISE_BAND_PCT = 5.0  # +/- this many points vs expected = surprise


def load_watchlist():
    return json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))


def growth_flag(expected_pct, actual_pct):
    if actual_pct is None:
        return "UNKNOWN"
    delta = actual_pct - expected_pct
    if delta > GROWTH_SURPRISE_BAND_PCT:
        return "POSITIVE"
    if delta < -GROWTH_SURPRISE_BAND_PCT:
        return "NEGATIVE"
    return "IN_LINE"


def build_item(company):
    tk = company["tk"]
    data = fetch(tk)
    momentum = compute_momentum(data.closes) if data.closes else None

    return {
        "tk": tk,
        "co": company["co"],
        "ex": company.get("ex", ""),
        "market_cap": data.market_cap,
        "pe_ltm": data.pe_ltm,
        "expected_eps_growth_pct": company["expected_eps_growth_pct"],
        "actual_eps_growth_pct": data.actual_eps_growth_pct,
        "growth_flag": growth_flag(company["expected_eps_growth_pct"], data.actual_eps_growth_pct),
        "price": momentum.price if momentum else None,
        "sma_50": momentum.sma_50 if momentum else None,
        "sma_200": momentum.sma_200 if momentum else None,
        "golden_cross": momentum.golden_cross if momentum else None,
        "roc_3m_pct": momentum.roc_3m_pct if momentum else None,
        "roc_3m_prior_pct": momentum.roc_3m_prior_pct if momentum else None,
        "momentum_flag": momentum.momentum_flag if momentum else "INSUFFICIENT_DATA",
    }


def run():
    today_iso = date.today().isoformat()
    watchlist = load_watchlist()

    if not watchlist:
        print("Watchlist is empty — nothing to do.")
        items = []
    else:
        print(f"Pulling data for {len(watchlist)} tickers...")
        items = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(build_item, c): c["tk"] for c in watchlist}
            for future in as_completed(futures):
                tk = futures[future]
                try:
                    items.append(future.result())
                except Exception as e:  # noqa: BLE001 — one bad ticker shouldn't kill the run
                    print(f"WARNING: failed to fetch {tk}: {e}", file=sys.stderr)
        # Keep output order stable and matching watchlist.json order.
        by_tk = {i["tk"]: i for i in items}
        items = [by_tk[c["tk"]] for c in watchlist if c["tk"] in by_tk]

    HISTORY_DIR.mkdir(exist_ok=True)
    history_payload = {
        "date": today_iso,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    (HISTORY_DIR / f"{today_iso}.json").write_text(
        json.dumps(history_payload, indent=2), encoding="utf-8"
    )

    render_site(today_iso, history_payload, watchlist)

    positive = [i for i in items if i["growth_flag"] == "POSITIVE"]
    negative = [i for i in items if i["growth_flag"] == "NEGATIVE"]
    accelerating = [i for i in items if i["momentum_flag"] == "ACCELERATING"]
    print(f"\nWatchlist {today_iso} — {len(items)} tickers, "
          f"{len(positive)} positive growth surprise, {len(negative)} negative, "
          f"{len(accelerating)} accelerating")
    for i in positive:
        print(f"  [GROWTH+] {i['tk']}: expected {i['expected_eps_growth_pct']}% vs actual {i['actual_eps_growth_pct']:.1f}%")
    for i in accelerating:
        print(f"  [ACCEL]   {i['tk']}: 3m RoC {i['roc_3m_pct']:.1f}% vs prior {i['roc_3m_prior_pct']:.1f}%")


if __name__ == "__main__":
    run()
