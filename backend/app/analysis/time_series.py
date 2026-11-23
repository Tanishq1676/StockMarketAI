"""Historical time-series service: caching + 5Y trend analysis."""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Dict, List, Optional

import pandas as pd

from ..database import SessionLocal
from ..data import providers
from ..models import HistoricalPrice
from . import indicators


def _closes_of(rows) -> List[float]:
    return [float(r.close) for r in rows]


def _lows_of(rows) -> List[float]:
    return [float(r.low) for r in rows]


def _highs_of(rows) -> List[float]:
    return [float(r.high) for r in rows]


def _volume_of(rows) -> List[int]:
    return [int(r.volume) for r in rows]


def get_cached_history(symbol: str, start_date: str, end_date: str, min_rows: int = 1,
                       ttl_days: int = 7) -> List[providers.HistoryRow]:
    """Read official stored history; never synthesise a replacement.

    Stock history lives in ``historical_price``.  Index history is written to
    both ``historical_price`` and ``index_history``; the latter is used as a
    fallback so an index chart still works if only the canonical table exists.
    """
    db = SessionLocal()
    try:
        q = (
            db.query(HistoricalPrice)
            .filter(
                HistoricalPrice.symbol == symbol,
                HistoricalPrice.date >= start_date,
                HistoricalPrice.date <= end_date,
            )
            .order_by(HistoricalPrice.date)
            .all()
        )
        if not q:
            from ..models import IndexHistory

            q = (
                db.query(IndexHistory)
                .filter(
                    IndexHistory.symbol == symbol,
                    IndexHistory.date >= start_date,
                    IndexHistory.date <= end_date,
                )
                .order_by(IndexHistory.date)
                .all()
            )
        return [
            providers.HistoryRow(
                r.date, r.open, r.high, r.low, r.close, r.volume,
                source=getattr(r, "source", "unknown"),
            )
            for r in q
        ]
    finally:
        db.close()


def fetch_history(symbol: str, start_date: str, end_date: str, exchange: str = "NSE") -> List[providers.HistoryRow]:
    """Official stored history only.

    A missing series returns an empty list instead of synthetic candles, so a
    chart can never imply that fabricated prices are real.
    """
    return get_cached_history(symbol, start_date, end_date)


def last_n_closes(rows: List[providers.HistoryRow], n: int) -> List[float]:
    return [float(r.close) for r in rows][-n:]


def time_series_report(symbol: str, days: int = 5 * 252) -> Dict[str, object]:
    """Five-year trend report for one symbol: MAs, RSI, MACD, BB, SR levels."""
    start = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = fetch_history(symbol, start, date.today().strftime("%Y-%m-%d"))
    if not rows:
        return {"symbol": symbol, "error": "no official history available", "data_source": "unavailable"}

    closes = _closes_of(rows)
    opens = [float(r.open) for r in rows]
    highs = _highs_of(rows)
    lows = _lows_of(rows)
    volumes = _volume_of(rows)
    dates = [r.date for r in rows]
    source = rows[-1].source if hasattr(rows[-1], "source") else "demo"
    n = len(closes)

    def tail(series, k=5):
        return series[-k:] if series else []

    rsi_series = indicators.rsi(closes, 14)
    macd_res = indicators.macd(closes, 12, 26, 9)
    bb = indicators.bollinger_bands(closes, 20, 2.0)
    sr = indicators.support_resistance(closes, max_levels=6)
    atr = indicators.volatility_atr(highs, lows, closes, 14)
    hv = indicators.historical_volatility(closes, 30)
    max_dd, _ = indicators.max_drawdown(closes)

    # Simple crossovers summary (boolean arrays -> last few events)
    ma5 = indicators.sma(closes, 5)
    ma20 = indicators.sma(closes, 20)
    ma50 = indicators.sma(closes, 50)
    ma100 = indicators.sma(closes, 100)
    ma200 = indicators.sma(closes, 200)
    crossings = indicators.moving_average_crossings(ma50, ma200)

    # Volume statistics
    avg_v = float(sum(volumes[-60:]) / max(len(volumes[-60:]), 1)) if volumes else 0.0
    last_v = float(volumes[-1]) if volumes else 0.0
    vol_spike = (last_v / avg_v) if avg_v > 0 else 1.0

    # Price change summary
    def pct_change(series, offset=0):
        if len(series) < offset + 2:
            return float("nan")
        base = series[len(series) - 1 - offset]
        cur = series[-1 - offset] if offset == 0 else series[-1 - offset]
        return (cur - base) / max(base, 1e-9) * 100.0 if base else float("nan")

    return {
        "symbol": symbol,
        "data_source": source,
        "days_of_history": n,
        "dates": dates,
        "closes": [round(c, 2) for c in closes],
        "opens": [round(o, 2) for o in opens],
        "highs": [round(h, 2) for h in highs],
        "lows": [round(l, 2) for l in lows],
        "volumes": volumes,
        "price_change_pct": round(pct_change(closes), 3) if not math.isnan(pct_change(closes)) else 0.0,
        "ma": {
            "ma5": _tail_nan_aware(ma5),
            "ma20": _tail_nan_aware(ma20),
            "ma50": _tail_nan_aware(ma50),
            "ma100": _tail_nan_aware(ma100),
            "ma200": _tail_nan_aware(ma200),
        },
        "rsi14_last": _last_valid(rsi_series),
        "macd": {
            "macd_last": _last_valid(macd_res["macd"]),
            "signal_last": _last_valid(macd_res["signal"]),
            "hist_last": _last_valid(macd_res["hist"]),
        },
        "bollinger": {
            "upper_last": _last_valid(bb["upper"]),
            "middle_last": _last_valid(bb["middle"]),
            "lower_last": _last_valid(bb["lower"]),
            "bandwidth_last": (
                round((bb["upper"][-1] - bb["lower"][-1]) / bb["middle"][-1], 4)
                if bb["upper"] and bb["lower"] and bb["middle"] and not math.isnan(bb["middle"][-1])
                else None
            ),
        },
        "support_levels": [round(float(x), 2) for x in sr],
        "atr14_last": _last_valid(atr),
        "historical_volatility_annualized": round(hv * 100.0, 4) if not math.isnan(hv) else None,
        "max_drawdown_pct": round(max_dd, 3) if max_dd else 0.0,
        "volume_avg_60d": round(avg_v, 1),
        "volume_last": last_v,
        "volume_ratio": round(vol_spike, 3),
        "ma50_ma200_crossovers_recent": crossings[-3:] if crossings else [],
        "trend": indicators.trend_summary(closes)["trend"],
        "recent_trend": indicators.trend_summary(closes)["recent_change_pct"],
    }


def _last_valid(series) -> Optional[float]:
    if not series:
        return None
    for x in reversed(series):
        if x is not None and not (isinstance(x, float) and math.isnan(x)):
            return float(x)
    return None


def _tail_nan_aware(series, k: int = 3):
    return [round(float(x), 2) if x is not None and not (isinstance(x, float) and math.isnan(x)) else None
            for x in series[-k:]]
