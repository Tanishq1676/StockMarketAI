"""BUY / SELL / HOLD signal engine (Phase 8).

Computes decision-support signals for stocks using the rule-based engine
as the deterministic baseline plus Ollama-generated explanatory text when
available. Signals always reference the verified current price and carry
risk/entry/target/stop-loss fields computed by the engine.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..ai.ai_service import ai_service
from ..database import SessionLocal
from ..models import Signal, StockMeta

logger = logging.getLogger(__name__)

SUPPORTED_SIGNAL_TYPES = ("BUY", "SELL", "HOLD", "WAIT_FOR_CONFIRMATION")


class SignalEngine:
    def __init__(self, ai: "ai_service.AIService"):
        self.ai = ai

    def signal_for_symbol(
        self,
        symbol: str,
        technical: Dict[str, object],
        predictions: Optional[List[Dict[str, object]]] = None,
        news_sentinel_score: float = 0.0,
        persist: bool = True,
        store: bool = True,
    ) -> Signal:
        signal = self.ai.signal_for_stock(
            symbol=symbol,
            technical=technical,
            predictions=predictions,
            news_sentinel_score=news_sentinel_score,
            persist=persist,
        )
        if store:
            db = SessionLocal()
            try:
                signal = db.merge(signal)
                db.commit()
            except Exception as exc:
                logger.warning("could not store signal for %s: %s", symbol, exc)
                db.rollback()
            finally:
                db.close()
        return signal

    def top_signals(self, n: int = 10, signal_type: Optional[str] = None) -> List[Dict]:
        db = SessionLocal()
        try:
            q = db.query(Signal).order_by(Signal.confidence.desc(), Signal.generated_at.desc())
            if signal_type:
                q = q.filter(Signal.signal_type == signal_type)
            signals = q.limit(n * 5).all()
            # pick the most recent per symbol
            seen, out = set(), []
            for s in signals:
                if s.symbol in seen:
                    continue
                seen.add(s.symbol)
                out.append(self._to_dict(s))
                if len(out) >= n:
                    break
            return out
        finally:
            db.close()

    def _to_dict(self, s: Signal) -> Dict:
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
            "ai_summary": s.ai_summary,
            "ai_source": s.ai_source or "rule_engine",
            "generated_at": s.generated_at.isoformat() if s.generated_at else None,
            "news_sentiment_score": round(float(s.news_sentiment_score), 3) if s.news_sentiment_score is not None else 0.0,
        }


signal_engine = SignalEngine(ai_service)
