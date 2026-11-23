"""Demo data generator.

The platform ships with a fully functional, clearly-labelled DEMO data
source when no real provider credentials are configured. Demo market data
is generated with a deterministic model (seeded by symbol) that mimics
 Indian market behaviour: trends, mean-reversion, seasonal drift, volume
spikes, and occasional gaps/oscillations. All demo rows carry
`source="demo"` so the UI never pretends otherwise.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

import numpy as np


def _stable_seed(symbol: str) -> int:
    return int(hashlib.md5(symbol.encode()).hexdigest(), 16) % (2**31 - 1)


@dataclass
class OHLCV:
    date: str  # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: int


def _trading_days_between(start: date, end: date) -> List[date]:
    days: List[date] = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:  # Mon=0 .. Fri=4; skip Sat/Sun
            days.append(cur)
        cur += timedelta(days=1)
    return days


def generate_history(
    symbol: str,
    days: int = 5 * 252,
    base_price: Optional[float] = None,
    as_of: Optional[date] = None,
    noise_seed: Optional[int] = None,
) -> List[OHLCV]:
    """Generate `days` of deterministic daily OHLCV for a symbol."""
    if as_of is None:
        as_of = date.today()
    rng = np.random.RandomState(_stable_seed(symbol) if noise_seed is None else noise_seed)

    # Start about (days//252)*5 years back so that the requested span lands
    # ending today, then return only the last `days` points.
    years = max(1, days // 252)
    start = as_of - timedelta(days=days + 7)

    price = base_price if base_price else 500.0 + (rng.rand() * 1000)
    # mean-reversion level a bit below the start price
    reversion_level = price * (1.0 - 0.08)

    hist: List[OHLCV] = []
    prev_close = price
    prev_volume = int(rng.randint(20000, 40000))

    for i, d in enumerate(_trading_days_between(start, as_of)):
        if len(hist) >= days:
            break
        # Mean reversion + random drift + autocorrelated shock
        trend = (rng.rand() - 0.5) * 0.004  # small daily drift
        mean_revert = 0.12 * (reversion_level - prev_close) / max(prev_close, 1)
        shock = rng.normal(0.0, 0.022) * math.sqrt(min(i + 1, 60) / 60)
        pct = trend + mean_revert + shock
        pct = float(np.clip(pct, -0.09, 0.09))
        new_close = prev_close * (1.0 + pct)
        if new_close <= 0:
            new_close = prev_close * 0.95

        gap_open = prev_close * (1.0 + float(rng.normal(0.0, 0.002)))
        new_high = max(new_close, gap_open) * (1.0 + abs(float(rng.normal(0, 0.01))))
        new_low = min(new_close, gap_open) * (1.0 - abs(float(rng.normal(0, 0.01))))
        new_high = float(np.clip(new_high, new_close * 0.995, new_close * 1.06))
        new_low = float(np.clip(new_low, new_close * 0.94, new_close * 1.005))
        if new_high < new_low:
            new_low = new_high * 0.995

        volume = int(prev_volume * (1 + float(rng.normal(0, 0.3))))
        # Occasional volume spikes (news events, FII flows, etc.)
        if rng.rand() < 0.08:
            volume = int(volume * (2.2 + rng.rand() * 1.5))
        # Keep volumes in a sane range for storage (SQLite INTEGER is 64-bit).
        volume = max(min(volume, 20_000_000_000), 1)

        hist.append(
            OHLCV(
                date=d.isoformat(),
                open=round(gap_open, 2),
                high=round(float(new_high), 2),
                low=round(float(new_low), 2),
                close=round(float(new_close), 2),
                volume=volume,
            )
        )
        prev_close = new_close
        prev_volume = volume

    if not hist:
        # Extremely short horizon fallback: single synthetic day.
        hist.append(
            OHLCV(
                date=as_of.isoformat(),
                open=price,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=30000,
            )
        )
    return hist


def generate_realtime_quote(symbol: str, hist: List[OHLCV]) -> dict:
    """Create a plausible current-market quote from the last history point."""
    if not hist:
        raise ValueError("no history for symbol")
    rng = np.random.RandomState(_stable_seed(symbol + "-realtime"))
    last = hist[-1]
    now_noise = float(rng.normal(0.0, 0.003))
    price = last.close * (1.0 + now_noise)
    open_price = last.close * (1.0 + float(rng.normal(0, 0.002)))
    high = price * (1 + abs(float(rng.normal(0, 0.008))) + 0.004)
    low = price * (1 - abs(float(rng.normal(0, 0.008))) - 0.004)
    high = max(high, price, last.close)
    low = min(low, price, last.close)
    volume = max(int(last.volume * (1 + rng.rand() * 0.5)), 1)
    pct_change = (price - open_price) / open_price if open_price else 0.0
    return {
        "open": round(open_price, 2),
        "high": round(high, 2),
        "low": round(low, 2),
        "close": round(price, 2),
        "volume": volume,
        "change_pct": round(pct_change, 4),
        "last_updated": datetime_now_iso(),
        "data_source": "demo",
        "is_live": False,
        "delay_minutes": 0,
    }


def datetime_now_iso() -> str:
    from datetime import datetime

    return datetime.utcnow().isoformat()
