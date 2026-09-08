"""Per-ticker data pull from Yahoo Finance via yfinance. No API key needed."""
from __future__ import annotations

from dataclasses import dataclass

import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class TickerData:
    market_cap: float | None
    pe_ltm: float | None
    actual_eps_growth_pct: float | None  # most-recent-quarter YoY
    closes: list[float]  # oldest-first daily closes, ~1y


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=20))
def fetch(tk: str) -> TickerData:
    ticker = yf.Ticker(tk)
    info = ticker.info

    market_cap = info.get("marketCap")
    pe_ltm = info.get("trailingPE")
    growth = info.get("earningsQuarterlyGrowth")
    actual_eps_growth_pct = growth * 100 if growth is not None else None

    hist = ticker.history(period="1y", interval="1d")
    closes = hist["Close"].dropna().tolist()

    return TickerData(
        market_cap=market_cap, pe_ltm=pe_ltm,
        actual_eps_growth_pct=actual_eps_growth_pct, closes=closes,
    )
