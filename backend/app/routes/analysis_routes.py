"""Analysis endpoint (Phase 3)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..ai.ai_service import ai_service
from ..analysis.time_series import fetch_history, time_series_report
from ..news.service import news_service
from ..predictions.engine import prediction_service

router = APIRouter()


@router.get("/analysis/{symbol}", tags=["analysis"])
def analysis_report(symbol: str):
    """Full five-year technical analysis + AI commentary for a stock."""
    symbol = symbol.upper()
    report = time_series_report(symbol)
    if not report.get("days_of_history"):
        raise HTTPException(404, f"{symbol} has no history")

    # AI summary of technicals
    ai = ai_service.analyze_stock(
        symbol,
        {k: report.get(k) for k in ("rsi14_last", "historical_volatility_annualized", "max_drawdown_pct",
                                    "price_change_pct", "recent_trend", "volume_ratio",
                                    "ma50", "ma200", "support_levels", "trend")},
        news=news_service.news_for_symbol(symbol, limit=8),
        predictions=_prediction_briefs(symbol),
    )
    report["ai_summary"] = ai["ai_summary"]
    report["ai_risk_factors"] = ai["ai_risk_factors"]
    report["ai_source"] = ai["ai_source"]
    report["sentiment_score"] = ai.get("sentiment_score") or 0.0
    report["news"] = news_service.news_for_symbol(symbol, limit=8)
    return report


def _prediction_briefs(symbol: str):
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        from ..models import Prediction

        rows = db.query(Prediction).filter(Prediction.symbol == symbol).order_by(Prediction.generated_at.desc()).limit(6).all()
        return [
            {
                "horizon": {"15min": 15, "30min": 30, "1hour": 60, "2hour": 120, "1day": 1440, "5days": 7200}.get(
                    _h(r.horizon_minutes), r.horizon_minutes
                ),
                "direction": r.direction,
                "confidence": r.confidence,
                "expected_move_pct": round((r.predicted_close - r.price_anchor) / r.price_anchor * 100, 3),
            }
            for r in rows
        ]
    finally:
        db.close()


def _h(minutes: int) -> str:
    m = {15: "15min", 30: "30min", 60: "1hour", 120: "2hour", 1440: "1day", 7200: "5days"}
    return m.get(minutes, str(minutes))
