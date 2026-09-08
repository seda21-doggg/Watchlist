"""Pure momentum calculations from a daily close-price series.

Two independent signals, deliberately kept separate rather than merged into
one score:
  - trend: price vs 50/200-day SMA, golden/death cross (1st derivative —
    direction).
  - acceleration: trailing 3-month return vs the prior 3-month return
    (2nd derivative — is the rate of change itself speeding up or slowing
    down; the Druckenmiller framing).
"""
from __future__ import annotations

from dataclasses import dataclass

TRADING_DAYS_3M = 63
ACCELERATION_FLAT_BAND_PCT = 2.0  # +/- this many points counts as FLAT


@dataclass
class MomentumResult:
    price: float
    sma_50: float | None
    sma_200: float | None
    golden_cross: bool | None
    roc_3m_pct: float | None
    roc_3m_prior_pct: float | None
    momentum_flag: str  # ACCELERATING / DECELERATING / FLAT / INSUFFICIENT_DATA


def _sma(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def _roc_pct(closes: list[float], end_offset: int, window: int) -> float | None:
    """% change over `window` trading days, ending `end_offset` days before
    the most recent close (end_offset=0 means ending today)."""
    end_idx = len(closes) - end_offset
    start_idx = end_idx - window
    if start_idx < 0 or end_idx <= 0 or end_idx > len(closes):
        return None
    start, end = closes[start_idx], closes[end_idx - 1]
    if start == 0:
        return None
    return (end - start) / start * 100


def compute_momentum(closes: list[float]) -> MomentumResult:
    """`closes` must be oldest-first daily closing prices."""
    if not closes:
        raise ValueError("closes must be non-empty")

    price = closes[-1]
    sma_50 = _sma(closes, 50)
    sma_200 = _sma(closes, 200)
    golden_cross = (sma_50 > sma_200) if (sma_50 is not None and sma_200 is not None) else None

    roc_now = _roc_pct(closes, end_offset=0, window=TRADING_DAYS_3M)
    roc_prior = _roc_pct(closes, end_offset=TRADING_DAYS_3M, window=TRADING_DAYS_3M)

    if roc_now is None or roc_prior is None:
        momentum_flag = "INSUFFICIENT_DATA"
    else:
        delta = roc_now - roc_prior
        if delta > ACCELERATION_FLAT_BAND_PCT:
            momentum_flag = "ACCELERATING"
        elif delta < -ACCELERATION_FLAT_BAND_PCT:
            momentum_flag = "DECELERATING"
        else:
            momentum_flag = "FLAT"

    return MomentumResult(
        price=price, sma_50=sma_50, sma_200=sma_200, golden_cross=golden_cross,
        roc_3m_pct=roc_now, roc_3m_prior_pct=roc_prior, momentum_flag=momentum_flag,
    )
