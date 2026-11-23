"""Predictions endpoints (Phase 7).

Returned forecasts always include predicted range + intervals, expected
direction, probabilities, confidence and supporting factors. Numerical
values come from the statistical/ML model on verified data.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..analysis.time_series import fetch_history
from ..database import SessionLocal
from ..models import HistoricalPrice, Prediction
from ..predictions.engine import prediction_service

router = APIRouter()

HORIZON_MAP = {"15min": 15, "30min": 30, "1hour": 60, "2hour": 120, "1day": 1440, "5days": 7200}


@router.get("/predictions/{symbol}", tags=["predictions"])
def get_predictions(symbol: str, horizon: Optional[str] = None):
    symbol = symbol.upper()
    db = SessionLocal()
    try:
        if not db.query(HistoricalPrice).filter(HistoricalPrice.symbol == symbol).first():
            # ensure there is history; otherwise no predictions can be generated
            from datetime import date, timedelta

            rows = fetch_history(symbol, (date.today() - timedelta(days=90)).strftime("%Y-%m-%d"), date.today().strftime("%Y-%m-%d"))
            if not rows:
                raise HTTPException(404, f"{symbol} has no history")

        q = db.query(Prediction).filter(Prediction.symbol == symbol)
        if horizon:
            minutes = HORIZON_MAP.get(horizon)
            if minutes is None:
                raise HTTPException(400, f"unsupported horizon {horizon}")
            q = q.filter(Prediction.horizon_minutes == minutes)
        rows = q.order_by(Prediction.generated_at.desc()).limit(60).all()
        out = []
        seen_horizons = set()
        for r in rows:
            # Keep only the newest forecast per horizon.
            if r.horizon_minutes in seen_horizons:
                continue
            seen_horizons.add(r.horizon_minutes)
            features = r.features if isinstance(r.features, list) else []
            interval_width_pct = float(features[1]) if len(features) > 1 else 0.0
            half_width = abs(r.price_anchor or 0.0) * interval_width_pct / 200.0
            interval = [
                round(r.predicted_close - half_width, 2),
                round(r.predicted_close + half_width, 2),
            ] if half_width > 0 else [r.predicted_close, r.predicted_close]
            confidence = float(r.confidence or 0.5)
            if r.direction == "up":
                bull, bear = confidence, 1.0 - confidence
            elif r.direction == "down":
                bull, bear = 1.0 - confidence, confidence
            else:
                bull = bear = 0.5
            out.append(
                {
                    "symbol": symbol,
                    "horizon_minutes": r.horizon_minutes,
                    "horizon": _inv_horizon(r.horizon_minutes),
                    "predicted_close": r.predicted_close,
                    "prediction_interval": interval,
                    "direction": r.direction,
                    "bullish_probability": round(bull, 3),
                    "bearish_probability": round(bear, 3),
                    "confidence": r.confidence,
                    "price_anchor": r.price_anchor,
                    "expected_move_pct": round((r.predicted_close - r.price_anchor) / r.price_anchor * 100, 3),
                    "model_type": r.model_type,
                    "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                    "data_source": "predictions_engine",
                }
            )
        out.sort(key=lambda x: x["horizon_minutes"])
        return {"symbol": symbol, "predictions": out}
    finally:
        db.close()


def _inv_horizon(minutes: int) -> str:
    return {v: k for k, v in HORIZON_MAP.items()}.get(minutes, str(minutes))


@router.post("/predictions/generate/{symbol}", tags=["predictions"])
def generate_predictions(symbol: str):
    """Generate fresh forecasts (15m..5d) for a symbol and persist them."""
    current = None
    try:
        from ..data import providers

        current = providers.get_quote(symbol).close
    except Exception:
        current = None
    forecasts = prediction_service.generate_for_symbol(symbol, current_price=current)
    return {"symbol": symbol, "forecasts": forecasts, "data_source": "predictions_engine"}


@router.get("/predictions/accuracy", tags=["predictions"])
def prediction_accuracy(symbol: Optional[str] = None, horizon: Optional[int] = None):
    report = prediction_service.accuracy_report(symbol=symbol, horizon=horizon)
    if horizon and horizon not in HORIZON_MAP.values():
        raise HTTPException(400, "unsupported horizon minutes")
    return report
