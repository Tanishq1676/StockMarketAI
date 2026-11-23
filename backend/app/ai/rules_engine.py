"""Rule-based market reasoning engine.

Deterministic, always-available reasoning used (a) whenever Ollama is not
reachable, and (b) to cross-check/validate Ollama output. All numbers here
come from verified data passed in by the caller (indicators, history,
predictions, news sentiment). The rule engine itself produces no prices.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from ..models import Signal


def _f(v) -> Optional[float]:
    try:
        v = float(v)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _ma_last(technical: Dict[str, object], key: str) -> Optional[float]:
    """Read the latest moving-average value.

    ``time_series_report`` exposes MAs as ``{"ma": {"ma50": [...]}}``; older
    callers passed a flat ``ma50`` number.  Support both shapes so the rule
    engine sees the same verified trend data the charts show.
    """
    ma = technical.get("ma")
    if isinstance(ma, dict):
        series = ma.get(key)
        if isinstance(series, (list, tuple)):
            for value in reversed(series):
                parsed = _f(value)
                if parsed is not None:
                    return parsed
    return _f(technical.get(key))


def analyze_stock_rules(
    symbol: str,
    technical: Dict[str, object],
    news: Optional[List[Dict[str, float]]] = None,
    predictions: Optional[List[Dict[str, object]]] = None,
) -> Dict[str, object]:
    """Produce a natural-language summary + reasoning points (rule based)."""
    rsi = _f(technical.get("rsi14_last"))
    trend = technical.get("trend", "sideways")
    recent_trend = _f(technical.get("recent_trend")) or 0.0
    hv = _f(technical.get("historical_volatility_annualized")) or 0.0
    ratio = _f(technical.get("volume_ratio")) or 1.0
    support = _f((technical.get("support_levels") or [None])[-1])
    m_50 = _ma_last(technical, "ma50")
    m_200 = _ma_last(technical, "ma200")
    news = news or []
    preds = predictions or []

    points: List[str] = []
    sentiment_contribs: List[float] = []

    # --- Trend / MA analysis ---
    if m_50 is not None and m_200 is not None:
        if m_50 > m_200:
            points.append("50-day MA trading above 200-day MA (golden-cross side).")
            sentiment_contribs.append(0.2)
        elif m_50 < m_200:
            points.append("50-day MA trading below 200-day MA (death-cross side).")
            sentiment_contribs.append(-0.2)

    if rsi is not None:
        if rsi > 70:
            points.append(f"RSI at {rsi:.1f} signals overbought; watch for a pullback.")
            sentiment_contribs.append(-0.15)
        elif rsi < 30:
            points.append(f"RSI at {rsi:.1f} signals oversold territory.")
            sentiment_contribs.append(0.15)
        elif 50 < rsi < 70:
            points.append(f"RSI at {rsi:.1f} supports momentum.")
            sentiment_contribs.append(0.1)
        elif rsi < 50 > 0:
            pass

    if recent_trend > 0.4:
        points.append(f"Recent 20-day trend is bullish (+{recent_trend}%).")
        sentiment_contribs.append(0.15)
    elif recent_trend < -0.4:
        points.append(f"Recent 20-day trend is bearish ({recent_trend}%).")
        sentiment_contribs.append(-0.15)

    # Volume
    if ratio >= 2.0:
        points.append("Volume above 2x the 60-day average: significant activity.")
        sentiment_contribs.append(0.1)
    elif ratio >= 1.5:
        points.append("Volume above average with no extreme spike.")
    elif ratio < 0.7:
        points.append("Volume below average: weakened participation.")
        sentiment_contribs.append(-0.1)

    # Volatility
    if hv is not None:
        if hv > 60:
            points.append("Historical volatility above 60% annualized: high risk.")
        elif hv > 40:
            points.append("Moderate volatility (≈ %s%% annualized)." % f"{hv:.0f}")
        else:
            points.append("Low volatility environment: favorable for accumulation.")
            sentiment_contribs.append(0.1)

    if support:
        points.append(f"Nearest support observed near {support:.2f}.")

    # --- News ---
    pos = [n for n in news if n.get("impact") == "positive"]
    neg = [n for n in news if n.get("impact") == "negative"]
    if pos:
        points.append(f"{len(pos)} recent positive news item(s) affecting {symbol}.")
        sentiment_contribs.append(0.15)
    if neg:
        points.append(f"{len(neg)} recent negative news item(s) affecting {symbol}.")
        sentiment_contribs.append(-0.15)

    # --- Predictions ---
    if preds:
        up = [p for p in preds if p.get("direction") == "up"]
        down = [p for p in preds if p.get("direction") == "down"]
        if up and down:
            points.append("Model forecasts are mixed: some horizons bullish, some bearish.")
        elif up:
            points.append("ML forecasts point to an upward bias over the next days.")
            sentiment_contribs.append(0.1)
        elif down:
            points.append("ML forecasts point to a downward bias over the next days.")
            sentiment_contribs.append(-0.1)

    sentiment = round(max(min(sum(sentiment_contribs) / max(len(sentiment_contribs), 1), 1.0), -1.0), 3) if sentiment_contribs else 0.0

    # Trend label
    trend_label = trend if isinstance(trend, str) else "sideways"

    # Risk label from volatility + support data
    if hv is not None and hv > 50:
        risk = "high"
    elif hv is not None and hv > 25:
        risk = "medium"
    else:
        risk = "low"

    summary = (
        f"Rule analysis of {symbol}: trend {trend_label.lower()} (vol {f'{hv:.0f}%' if hv else 'n/a'} annualized), "
        f"RSI {f'{rsi:.1f}' if rsi else 'n/a'}, sentiment score {sentiment:+.2f}, risk {risk}. "
        f"Recent move {f'{recent_trend:+.2f}' if recent_trend else 'n/a'}%. "
        + " ".join(points[:6])
    )
    return {
        "summary": summary,
        "trend": trend_label,
        "sentiment": sentiment,
        "risk_level": risk,
        "points": points,
    }


def rules_signal_for_stock(
    symbol: str,
    technical: Dict[str, object],
    predictions: Optional[List[Dict[str, object]]] = None,
    news_sentiment: float = 0.0,
    reason_limit: int = 8,
) -> Dict[str, object]:
    """Quantitative BUY/SELL/HOLD decision with continuous confidence.

    The conviction score blends trend, momentum, 20-day return, Bollinger
    position, volume, forecast consensus and news sentiment.  Target/stop are
    ATR-based and risk is classified from volatility, ATR and drawdown.
    """
    from .signal_model import quant_signal_decision

    decision = quant_signal_decision(symbol, technical, predictions or [], news_sentiment)
    decision["reasons"] = decision.get("reasons", [])[:reason_limit]
    decision["tech_reasons"] = decision.get("tech_reasons", [])[:reason_limit]
    return decision


def make_signal_record(
    symbol: str,
    decision: Dict[str, object],
    technical: Dict[str, object],
    predictions: Optional[List[Dict[str, object]]] = None,
    news_sentinel_score: float = 0.0,
    ai_summary: str = "",
    ai_source: str = "rule_engine",
    generated_at=None,
) -> Signal:
    """Build a Signal ORM object from a decision dict."""
    from datetime import datetime

    sig = Signal()
    sig.symbol = symbol
    sig.signal_type = decision["signal_type"]
    sig.confidence = decision["confidence"]
    sig.reasons = decision.get("reasons", [])
    sig.news_sentiment_score = news_sentinel_score
    sig.tech_reasons = decision.get("tech_reasons", [])
    sig.fund_reasons = decision.get("fund_reasons", [])
    sig.risk_level = decision.get("risk_level") or technical.get("risk_level", "medium")
    sig.generated_at = generated_at or datetime.utcnow()
    sig.ai_summary = ai_summary

    entry = decision.get("entry_price")
    target = decision.get("target_price")
    stop = decision.get("stop_loss")
    if entry is not None and target is not None and stop is not None:
        sig.entry_price = entry
        sig.target_price = target
        sig.stop_loss = stop
        sig.risk_reward = decision.get("risk_reward", 0.0)
        sig.expected_holding_minutes = int(decision.get("expected_holding_minutes") or 0)
        return sig

    # Fallback for older callers that supply only a decision label.
    preds = predictions or []
    if preds:
        best = max(preds, key=lambda p: p.get("confidence", 0))
        entry = best.get("predicted_close")
        target = entry * 1.015 if decision["signal_type"] in ("BUY", "WAIT_FOR_CONFIRMATION") else entry * 0.985
        stop = entry * (1 - 0.02) if decision["signal_type"] in ("BUY", "WAIT_FOR_CONFIRMATION") else entry * 1.02
        holding = best.get("expected_holding_minutes", 0)
    else:
        close = _f(technical.get("closes", [0])[-1]) if technical.get("closes") else 0.0
        entry = close
        target = close * 1.02
        stop = close * 0.98
        holding = 240
    risk_reward = ((target - entry) / abs(entry - stop)) if entry and stop and (entry - stop) != 0 else 0.0
    sig.entry_price = entry
    sig.target_price = round(target, 2)
    sig.stop_loss = round(stop, 2)
    sig.risk_reward = round(risk_reward, 3)
    sig.expected_holding_minutes = int(holding or 0)
    return sig
