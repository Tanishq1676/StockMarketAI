"""Quantitative signal ensemble for BUY / SELL / HOLD decisions.

The old rule engine mapped a small integer score to a confidence of either
0.55 (WAIT/HOLD) or 0.69-0.78 (BUY/SELL) and used fixed +/-2% target/stop
levels.  This module replaces that with a continuous conviction score built
from verified indicators and ATR-based risk levels, so every stock gets its
own confidence, target, stop and risk classification.

Every input comes from ``time_series_report`` (official NSE/BSE history) or
the prediction engine.  Nothing is invented here: when a feature is missing
it is simply left out of the ensemble and the remaining weights are
renormalised.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

MODEL_NAME = "quant_ensemble_v1"


# ---------------------------------------------------------------------------
# Small numeric helpers
# ---------------------------------------------------------------------------

def _f(value) -> Optional[float]:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


def _last(series) -> Optional[float]:
    if isinstance(series, (list, tuple)):
        for value in reversed(series):
            parsed = _f(value)
            if parsed is not None:
                return parsed
        return None
    return _f(series)


def _ma(technical: Dict[str, Any], key: str) -> Optional[float]:
    ma = technical.get("ma")
    if isinstance(ma, dict):
        value = _last(ma.get(key))
        if value is not None:
            return value
    return _f(technical.get(key))


def _clip(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _squash(value: float) -> float:
    """Smoothly map an unbounded number into [-1, 1]."""
    return math.tanh(value)


def _weighted_mean(parts: Sequence[Tuple[Optional[float], float]]) -> Optional[float]:
    total = sum(weight for value, weight in parts if value is not None and weight > 0)
    if total <= 0:
        return None
    return sum(value * weight for value, weight in parts if value is not None) / total


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

def _trend_feature(close, ma20, ma50, ma200) -> Optional[float]:
    parts: List[Tuple[Optional[float], float]] = []
    if close and ma20:
        parts.append((1.0 if close > ma20 else -1.0, 0.30))
    if ma20 and ma50:
        parts.append((1.0 if ma20 > ma50 else -1.0, 0.25))
    if ma50 and ma200:
        parts.append((1.0 if ma50 > ma200 else -1.0, 0.30))
    if close and ma200:
        parts.append((1.0 if close > ma200 else -1.0, 0.15))
    return _weighted_mean(parts)


def _momentum_feature(rsi, macd_hist, atr, close) -> Optional[float]:
    parts: List[Tuple[Optional[float], float]] = []
    if rsi is not None:
        parts.append((_clip((rsi - 50.0) / 18.0), 0.55))
    if macd_hist is not None:
        scale = atr if atr and atr > 0 else (close * 0.01 if close else None)
        if scale:
            parts.append((_squash(macd_hist / scale), 0.45))
    return _weighted_mean(parts)


def _return_feature(recent_pct, hv) -> Optional[float]:
    if recent_pct is None:
        return None
    daily_vol = (hv / math.sqrt(252.0)) if hv and hv > 0 else 1.2
    horizon_vol = daily_vol * math.sqrt(20.0)
    return _squash(recent_pct / horizon_vol) if horizon_vol > 0 else None


def _bollinger_feature(close, bollinger) -> Optional[float]:
    if not isinstance(bollinger, dict):
        return None
    upper = _f(bollinger.get("upper_last"))
    lower = _f(bollinger.get("lower_last"))
    if not close or upper is None or lower is None or upper <= lower:
        return None
    position = (close - lower) / (upper - lower)
    return _clip(2.0 * position - 1.0)


def _volume_feature(volume_ratio, direction_hint) -> Optional[float]:
    ratio = _f(volume_ratio)
    if ratio is None or ratio <= 0:
        return None
    strength = _clip(math.log(ratio) / math.log(2.0))
    return strength * (1.0 if direction_hint >= 0 else -1.0)


def _prediction_feature(predictions, hv) -> Optional[float]:
    if not predictions:
        return None
    moves = [_f(p.get("expected_move_pct")) for p in predictions]
    moves = [m for m in moves if m is not None]
    if not moves:
        return None
    mean_move = sum(moves) / len(moves)
    daily_vol = (hv / math.sqrt(252.0)) if hv and hv > 0 else 1.0
    scale = max(0.25, daily_vol * math.sqrt(2.0))
    direction = 0.0
    up = sum(1 for p in predictions if p.get("direction") == "up")
    down = sum(1 for p in predictions if p.get("direction") == "down")
    if up or down:
        direction = (up - down) / max(up + down, 1)
    return 0.6 * _squash(mean_move / scale) + 0.4 * direction


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

def quant_signal_decision(
    symbol: str,
    technical: Dict[str, Any],
    predictions: Optional[List[Dict[str, Any]]] = None,
    news_sentiment: float = 0.0,
) -> Dict[str, Any]:
    """Return a continuous signal decision with ATR-based risk levels."""
    preds = predictions or []
    closes = technical.get("closes") or []
    close = _last(closes)

    ma20 = _ma(technical, "ma20")
    ma50 = _ma(technical, "ma50")
    ma200 = _ma(technical, "ma200")
    rsi = _f(technical.get("rsi14_last"))
    macd = technical.get("macd") if isinstance(technical.get("macd"), dict) else {}
    macd_hist = _f(macd.get("hist_last"))
    atr = _f(technical.get("atr14_last"))
    hv = _f(technical.get("historical_volatility_annualized"))
    recent = _f(technical.get("recent_trend"))
    vol_ratio = _f(technical.get("volume_ratio"))
    days = _f(technical.get("days_of_history"))

    features: Dict[str, Optional[float]] = {
        "trend": _trend_feature(close, ma20, ma50, ma200),
        "momentum": _momentum_feature(rsi, macd_hist, atr, close),
        "return": _return_feature(recent, hv),
        "bollinger": _bollinger_feature(close, technical.get("bollinger")),
        "prediction": _prediction_feature(preds, hv),
    }
    direction_hint = 0.0
    for key in ("trend", "momentum", "return", "prediction"):
        if features.get(key) is not None:
            direction_hint += features[key]
    features["volume"] = _volume_feature(vol_ratio, direction_hint)
    features["news"] = _clip(news_sentiment) if news_sentiment else None

    weights = {
        "trend": 0.30,
        "momentum": 0.24,
        "return": 0.14,
        "bollinger": 0.08,
        "volume": 0.08,
        "prediction": 0.12,
        "news": 0.04,
    }
    score = _weighted_mean([(features.get(k), w) for k, w in weights.items()]) or 0.0
    strength = abs(score)

    if score >= 0.18:
        signal_type = "BUY"
    elif score <= -0.18:
        signal_type = "SELL"
    elif score >= 0.06:
        signal_type = "WAIT_FOR_CONFIRMATION"
    elif score <= -0.06:
        signal_type = "WAIT_FOR_CONFIRMATION"
    else:
        signal_type = "HOLD"

    # --- Risk classification from volatility, ATR and drawdown -------------
    # ``max_drawdown_pct`` is a positive magnitude (e.g. 24.5 means -24.5%).
    atr_pct = (atr / close * 100.0) if atr and close else 0.0
    max_dd = _f(technical.get("max_drawdown_pct")) or 0.0
    if (hv is not None and hv >= 50) or atr_pct >= 4.0 or max_dd >= 35.0:
        risk_level = "high"
    elif (hv is not None and hv >= 25) or atr_pct >= 2.0 or max_dd >= 20.0:
        risk_level = "medium"
    else:
        risk_level = "low"

    # --- Continuous confidence --------------------------------------------
    confidence = 0.50 + 0.40 * strength
    if hv is not None:
        confidence -= 0.08 * _clip((hv - 22.0) / 60.0, 0.0, 1.0)
    if atr_pct > 4.0:
        confidence -= 0.04
    if days is not None and days < 80:
        confidence -= 0.05
    if preds and features.get("prediction") is not None and score * features["prediction"] < 0:
        confidence -= 0.04
    confidence = round(_clip(confidence, 0.45, 0.93), 3)

    # --- ATR-based entry / target / stop ----------------------------------
    entry = close or 0.0
    if atr is None or atr <= 0:
        atr = (entry * (hv / 100.0) / math.sqrt(252.0)) if entry and hv else entry * 0.012
    atr = max(atr, entry * 0.003) if entry else atr

    bias = 1.0 if score >= 0 else -1.0
    target_mult = 2.2 + 0.8 * strength
    stop_mult = 1.1 + 0.3 * (1.0 - strength)
    target_dist = atr * target_mult
    stop_dist = atr * stop_mult

    if bias > 0:
        target = entry + target_dist
        stop = entry - stop_dist
    else:
        target = entry - target_dist
        stop = entry + stop_dist

    # Snap levels to nearby official support/resistance only when the snapped
    # level is still a meaningful distance away; otherwise keep the ATR level.
    if entry and atr and atr > 0:
        levels = sorted(
            level
            for level in (_f(x) for x in (technical.get("support_levels") or []))
            if level and level > 0
        )
        below = [level for level in levels if level < entry * 0.997]
        above = [level for level in levels if level > entry * 1.003]
        min_target = max(1.5 * atr, entry * 0.008)
        if bias > 0:
            if below:
                nearest = max(below)
                distance = entry - nearest
                if 0.8 * atr <= distance <= 1.8 * atr:
                    stop = nearest * 0.995
            if above:
                nearest = min(above)
                distance = nearest - entry
                if min_target <= distance <= 3.5 * atr:
                    target = min(target, nearest)
        else:
            if above:
                nearest = min(above)
                distance = nearest - entry
                if 0.8 * atr <= distance <= 1.8 * atr:
                    stop = nearest * 1.005
            if below:
                nearest = max(below)
                distance = entry - nearest
                if min_target <= distance <= 3.5 * atr:
                    target = max(target, nearest)

    if entry:
        floor = entry * 0.5
        stop = round(max(stop, floor), 2)
        target = round(max(target, floor), 2)
        entry = round(entry, 2)
    else:
        stop = target = 0.0
    risk_reward = (
        round(abs(target - entry) / abs(entry - stop), 3)
        if entry and stop and abs(entry - stop) > 1e-9
        else 0.0
    )
    holding_days = max(1, min(10, round(abs(target - entry) / atr))) if atr else 2
    holding_minutes = int(holding_days * 1440)

    # --- Human-readable rationale -----------------------------------------
    reasons: List[str] = []
    if close and ma50 and ma200:
        if ma50 > ma200:
            reasons.append("50-day MA above 200-day MA: bullish trend structure.")
        else:
            reasons.append("50-day MA below 200-day MA: bearish trend structure.")
    if close and ma20:
        reasons.append(
            f"Close {'above' if close > ma20 else 'below'} the 20-day MA "
            f"({ma20:,.2f})."
        )
    if rsi is not None:
        if rsi >= 70:
            reasons.append(f"RSI {rsi:.1f}: overbought, pullback risk.")
        elif rsi <= 30:
            reasons.append(f"RSI {rsi:.1f}: oversold, rebound potential.")
        else:
            reasons.append(f"RSI {rsi:.1f}: {'positive' if rsi >= 50 else 'soft'} momentum.")
    if macd_hist is not None:
        reasons.append(f"MACD histogram {'positive' if macd_hist >= 0 else 'negative'} ({macd_hist:,.3f}).")
    if recent is not None and hv:
        reasons.append(f"20-day move {recent:+.2f}% vs {hv:.1f}% annualised volatility.")
    if vol_ratio is not None:
        reasons.append(f"Volume {vol_ratio:.2f}x the 60-day average.")
    if preds:
        up = sum(1 for p in preds if p.get("direction") == "up")
        down = sum(1 for p in preds if p.get("direction") == "down")
        if up or down:
            reasons.append(f"Forecast consensus {up} up / {down} down across horizons.")
    if entry:
        reasons.append(
            f"ATR stop {abs(entry - stop) / entry * 100:.2f}% away, "
            f"target {abs(target - entry) / entry * 100:.2f}% away "
            f"(R:R {risk_reward:.2f})."
        )
    reasons.append(
        f"Risk {risk_level} from {hv:.1f}% volatility and {atr_pct:.2f}% ATR."
        if hv is not None
        else f"Risk {risk_level} from {atr_pct:.2f}% ATR."
    )

    return {
        "signal_type": signal_type,
        "confidence": confidence,
        "score": round(score, 4),
        "reasons": reasons[:8],
        "tech_reasons": reasons[:8],
        "fund_reasons": [],
        "risk_level": risk_level,
        "entry_price": entry,
        "target_price": target,
        "stop_loss": stop,
        "risk_reward": risk_reward,
        "expected_holding_minutes": holding_minutes,
        "model": MODEL_NAME,
        "features": {k: round(v, 4) if v is not None else None for k, v in features.items()},
    }
