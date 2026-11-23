"""Technical indicators for Indian stock analysis.

All functions are pure functions over price series (lists of floats).
Outputs are dicts / lists of floats. NaN-safe; short series yield NaN
outputs where the window is not yet filled.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def _s(series: List[float]) -> pd.Series:
    return pd.Series([float(x) for x in series if x is not None])


def sma(series: List[float], n: int) -> List[float]:
    if n <= 0 or len(series) < n:
        return [float("nan")] * len(series)
    arr = np.array(series, dtype=float)
    out = np.full(len(arr), np.nan)
    cs = np.concatenate(([0.0], np.cumsum(arr)))
    out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return [float(x) for x in out]


def ema(series: List[float], n: int) -> List[float]:
    if n <= 0 or len(series) == 0:
        return [float("nan")] * len(series)
    arr = pd.Series(np.array(series, dtype=float))
    return [float(x) for x in arr.ewm(span=n, adjust=False, min_periods=n).mean()]


def _price_at(series: List[float], offset: int = 0) -> List[float]:
    """series[offset] -> series[-1]"""
    if offset >= len(series):
        return []
    return series[offset:]


def rsi(series: List[float], n: int = 14) -> List[float]:
    """Wilder's Relative Strength Index over a series of closes."""
    if len(series) < n + 1:
        return [float("nan")] * len(series)
    arr = np.array(series, dtype=float)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    ag = np.zeros_like(deltas, dtype=float)
    al = np.zeros_like(deltas, dtype=float)
    # initial average
    ag[n - 1] = gains[:n].mean() if n > 0 else 0.0
    al[n - 1] = losses[:n].mean() if n > 0 else 0.0
    for i in range(n, len(deltas)):
        ag[i] = (ag[i - 1] * (n - 1) + gains[i]) / n
        al[i] = (al[i - 1] * (n - 1) + losses[i]) / n
    out = np.full(len(arr), np.nan)
    # al==0 with ag>0 -> RSI = 100 (rs=inf); ag==0 & al==0 -> 0
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(al > 0, ag / np.where(al > 0, al, 1.0), np.where(ag > 0, np.inf, 0.0))
    rs = np.nan_to_num(rs, nan=0.0, posinf=np.inf, neginf=0.0)
    out[n:] = 100.0 - (100.0 / (1.0 + rs[n - 1:]))
    return [float(x) for x in out]


def macd(series: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
    """MACD line, signal line and histogram (all lists, same length as input)."""
    ef = ema(series, fast)
    es = ema(series, slow)
    if len(series) < max(slow, fast):
        return {"macd": [float("nan")] * len(series), "signal": [float("nan")] * len(series),
                "hist": [float("nan")] * len(series)}
    macd_line = []
    for a, b in zip(ef, es):
        macd_line.append(a - b if not (math.isnan(a) or math.isnan(b)) else float("nan"))
    # drop leading NaNs for signal computation
    valid = [x for x in macd_line if not math.isnan(x)]
    if len(valid) < signal:
        return {"macd": [float("nan")] * len(series), "signal": [float("nan")] * len(series),
                "hist": [float("nan")] * len(series)}
    sig = ema(macd_line, signal)
    hist = [a - b if not (math.isnan(a) or math.isnan(b)) else float("nan") for a, b in zip(macd_line, sig)]
    return {"macd": macd_line, "signal": sig, "hist": hist}


def bollinger_bands(series: List[float], n: int = 20, std: float = 2.0) -> Dict[str, List[float]]:
    if len(series) < n:
        return {"upper": [float("nan")] * len(series), "middle": [float("nan")] * len(series),
                "lower": [float("nan")] * len(series)}
    arr = np.array(series, dtype=float)
    mean = sma(series, n)
    upper, lower = [], []
    for i in range(len(arr)):
        if i < n - 1 or math.isnan(mean[i]):
            upper.append(float("nan"))
            lower.append(float("nan"))
            continue
        window = arr[i - n + 1: i + 1]
        band = np.std(window) * std
        upper.append(mean[i] + band)
        lower.append(mean[i] - band)
    return {"upper": upper, "middle": mean, "lower": lower}


def support_resistance(series: List[float], max_levels: int = 6, min_swing: float = 1.5) -> List[float]:
    """Approximate support/resistance levels from swing highs/lows.

    Returns a list of (level, type) sorted with strongest first. Levels are
    prices where price repeatedly touched (a clustering over ~1% bands).
    """
    if len(series) < 20:
        return []
    highs = []
    lows = []
    # rolling local extrema
    for i in range(2, len(series) - 2):
        w = series[i - 2: i + 3]
        if series[i] == max(w):
            highs.append(series[i])
        if series[i] == min(w):
            lows.append(series[i])
    if not highs and not lows:
        return []
    levels = []
    for src in (highs, lows):
        src = sorted(src, reverse=True if src is highs else False)
        for price in src:
            if any(abs(price - l[0]) / max(l[0], 1e-9) < 0.012 for l in levels):
                continue
            # strength = number of touches within 1.5% band
            strength = sum(1 for p in series if abs(p - price) / max(price, 1e-9) < 0.015)
            levels.append((float(price), strength))
    levels.sort(key=lambda t: t[1], reverse=True)
    out = [float(l) for l, _ in levels[:max_levels]]
    return sorted(out)


def volatility_atr(series_high: List[float], series_low: List[float], series_close: List[float], n: int = 14) -> List[float]:
    if len(series_close) < n + 1:
        return [float("nan")] * len(series_close)
    tr = []
    for i in range(1, len(series_close)):
        h = series_high[i] - series_low[i]
        h2 = abs(series_high[i] - series_close[i - 1])
        l2 = abs(series_low[i] - series_close[i - 1])
        tr.append(max(h, h2, l2))
    out = [float("nan")] * len(series_close)
    running = []
    for i, v in enumerate(tr):
        running.append(v)
        if len(running) == n:
            out[i + 1] = float(np.mean(running))
        elif len(running) > n:
            running = running[1:]
            out[i + 1] = float(np.mean(running))
    return out


def historical_volatility(closes: List[float], n: int = 30, trading_days: int = 252) -> float:
    """Annualized historical volatility (std of log returns * sqrt(252))."""
    arr = np.array(closes[-n - 1:], dtype=float)
    if len(arr) < 3:
        return float("nan")
    rets = np.diff(np.log(arr))
    if len(rets) < 2:
        return float("nan")
    std = float(np.std(rets, ddof=1))
    return float(std * math.sqrt(trading_days))


def max_drawdown(closes: List[float]) -> Tuple[float, int]:
    """Returns (max_drawdown_pct, index_of_peak_in_closes)."""
    if len(closes) < 2:
        return 0.0, -1
    arr = np.array(closes, dtype=float)
    peak = arr[0]
    peak_idx = 0
    max_dd = 0.0
    max_dd_idx = 0
    for i, v in enumerate(arr):
        if v > peak:
            peak = v
            peak_idx = i
        dd = (peak - v) / max(peak, 1e-9)
        if dd > max_dd:
            max_dd = dd
            max_dd_idx = i
    return float(max_dd * 100), peak_idx


def moving_average_crossings(ma_short: List[float], ma_long: List[float]) -> List[Dict[str, object]]:
    """Detect golden/death crosses between two MA series (aligned)."""
    events = []
    prev = None
    for i, (a, b) in enumerate(zip(ma_short, ma_long)):
        if math.isnan(a) or math.isnan(b):
            continue
        cur = a > b
        if prev is not None and cur != prev:
            events.append(
                {
                    "index": i,
                    "event": "golden_cross" if cur else "death_cross",
                    "short_ma": float(a),
                    "long_ma": float(b),
                }
            )
        prev = cur
    return events


def trend_summary(closes: List[float]) -> Dict[str, object]:
    """Simple summary of recent trend direction over the given closes."""
    if len(closes) < 5:
        return {"trend": "insufficient_data", "recent_change_pct": 0.0}
    recent = closes[-20:]
    pct = (recent[-1] - recent[0]) / max(recent[0], 1e-9) * 100.0
    direction = "bullish" if pct > 0.3 else ("bearish" if pct < -0.3 else "sideways")
    return {"trend": direction, "recent_change_pct": round(pct, 3)}
