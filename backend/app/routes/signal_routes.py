"""Signal endpoints (Phase 8): decision-support for BUY/SELL/HOLD."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..analysis.time_series import fetch_history, time_series_report
from ..database import SessionLocal
from ..models import Signal
from ..signals.engine import signal_engine

router = APIRouter()


def _top_dict(s: Signal) -> dict:
    return {
        "symbol": s.symbol,
        "signal_type": s.signal_type,
        "confidence": round(float(s.confidence), 3),
        "entry_price": s.entry_price,
        "target_price": s.target_price,
        "stop_loss": s.stop_loss,
        "risk_reward": s.risk_reward,
        "expected_holding_minutes": s.expected_holding_minutes,
        "risk_level": s.risk_level,
        "reasons": s.reasons,
        "tech_reasons": s.tech_reasons,
        "fund_reasons": s.fund_reasons,
        "news_sentiment_score": round(float(s.news_sentiment_score), 3) if s.news_sentiment_score is not None else 0.0,
        "ai_summary": s.ai_summary,
        "ai_source": s.ai_source or "rule_engine",
        "generated_at": s.generated_at.isoformat() if s.generated_at else None,
    }


@router.get("/signals", tags=["signals"])
def get_top_signals(n: int = Query(10, ge=1, le=50), type: Optional[str] = None):
    if type and type not in ("BUY", "SELL", "HOLD", "WAIT_FOR_CONFIRMATION"):
        raise HTTPException(400, "invalid signal type")
    rows = signal_engine.top_signals(n=n, signal_type=type)
    return {"signals": rows, "count": len(rows)}


@router.get("/signals/{symbol}", tags=["signals"])
def latest_signal_for_symbol(symbol: str):
    db = SessionLocal()
    try:
        row = (
            db.query(Signal)
            .filter(Signal.symbol == symbol.upper())
            .order_by(Signal.generated_at.desc())
            .first()
        )
        return {"symbol": symbol.upper(), "signal": _top_dict(row) if row else None}
    finally:
        db.close()


@router.post("/signals/generate/{symbol}", tags=["signals"])
def generate_signal(symbol: str):
    """Generate a fresh signal for a symbol from verified technical data.

    Confidence, target and stop come from the quantitative ensemble
    (trend, momentum, volatility, volume, forecast consensus) and ATR-based
    risk levels, so each symbol gets its own values rather than a fixed label.
    """
    symbol = symbol.upper()
    analysis = time_series_report(symbol, days=5 * 252)
    if not analysis.get("days_of_history"):
        raise HTTPException(404, f"{symbol} has no history")

    close = None
    closes = analysis.get("closes") or []
    if closes:
        try:
            close = float(closes[-1])
        except (TypeError, ValueError):
            close = None

    predictions: list = []
    try:
        from ..predictions.engine import prediction_service

        predictions = prediction_service.preview_for_symbol(symbol, current_price=close)
    except Exception:  # forecasts are optional; the ensemble renormalises
        predictions = []

    signal = signal_engine.signal_for_symbol(
        symbol, analysis, predictions=predictions, persist=True, store=True
    )
    return {
        "symbol": symbol,
        "signal": _top_dict(signal),
        "data_source": analysis.get("data_source"),
        "forecast_horizons": len(predictions),
    }
