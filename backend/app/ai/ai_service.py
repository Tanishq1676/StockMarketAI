"""AI Market Reasoning Service (Phase 5).

Uses Ollama when available for natural-language explanations; when Ollama is
not reachable (or returns garbage) it falls back to the deterministic rule
engine, which always works. All numeric fields come from verified data;
the AI explains, it never invents numbers.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..ai.ollama_client import OllamaUnavailable, ollama_client
from ..ai.rules_engine import analyze_stock_rules, make_signal_record, rules_signal_for_stock
from ..database import SessionLocal
from ..models import Signal

logger = logging.getLogger(__name__)


def _clip(x: float) -> float:
    return float(min(max(x, -1.0), 1.0))


class AIService:
    def __init__(self):
        self._ollama_ok: Optional[bool] = None
        self._ollama_checked_at: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------
    def ollama_available(self, refresh: bool = False) -> bool:
        if not refresh and self._ollama_ok is not None and self._ollama_checked_at:
            if (datetime.utcnow() - self._ollama_checked_at).total_seconds() < 30:
                return self._ollama_ok
        ok = ollama_client.is_available()
        self._ollama_ok = ok
        self._ollama_checked_at = datetime.utcnow()
        return ok

    # ------------------------------------------------------------------
    # Stock analysis
    # ------------------------------------------------------------------
    def analyze_stock(
        self,
        symbol: str,
        technical: Dict[str, Any],
        news: Optional[List[Dict[str, Any]]] = None,
        predictions: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return verified technical analysis + AI natural-language summary."""
        news = news or []
        preds = predictions or []
        rules = analyze_stock_rules(symbol, technical, news, preds)

        ai_summary, ai_risk, ai_source = self._ai_explain(symbol, technical, news, preds, context, rules)
        sentiment = _clip(rules["sentiment"] + self._news_sentiment(news) * 0.3)

        result: Dict[str, Any] = {
            "symbol": symbol,
            "ai_summary": ai_summary,
            "trend": rules["trend"],
            "risk_level": rules["risk_level"],
            "ai_risk_factors": ai_risk,
            "ai_source": ai_source,
            "rule_points": rules["points"],
            "sentiment_score": round(sentiment, 3),
            "rules_summary": rules["summary"],
        }
        # Verified numbers from the technical layer
        for k in ("rsi14_last", "historical_volatility_annualized", "max_drawdown_pct",
                  "price_change_pct", "recent_trend", "volume_ratio", "volume_last",
                  "volume_avg_60d"):
            if k in technical and technical[k] is not None:
                v = technical[k]
                result[k] = round(float(v), 4) if isinstance(v, float) else v
        for k in ("ma5", "ma20", "ma50", "ma100", "ma200", "upper_last", "lower_last", "middle_last", "atr14_last"):
            if k in technical and technical[k] is not None:
                result[k] = round(float(technical[k]), 2)
        ma = technical.get("ma", {})
        for k, v in ma.items():
            if v:
                result[k] = v[-1]
        return result

    def _news_sentiment(self, news: List[Dict[str, Any]]) -> float:
        if not news:
            return 0.0
        scores = [float(n.get("sentiment_score", 0)) for n in news if n.get("symbol")]
        return sum(scores) / len(scores) if scores else 0.0

    def _ai_explain(self, symbol, technical, news, preds, context, rules) -> tuple:
        """Ask Ollama for explanation; fall back to rules on any failure."""
        data = {
            "symbol": symbol,
            "trend": rules["trend"],
            "sentiment": rules["sentiment"],
            "risk_level": rules["risk_level"],
            "technical": {
                "rsi": technical.get("rsi14_last"),
                "vol_annualized": technical.get("historical_volatility_annualized"),
                "max_drawdown_pct": technical.get("max_drawdown_pct"),
                "recent_trend_pct": technical.get("recent_trend"),
                "volume_ratio": technical.get("volume_ratio"),
                "ma50": technical.get("ma50"),
                "ma200": technical.get("ma200"),
                "support_levels": technical.get("support_levels"),
                "macd_hist_last": technical.get("macd", {}).get("hist_last"),
            },
            "predictions": [
                {
                    "horizon": p.get("horizon"),
                    "direction": p.get("direction"),
                    "confidence": p.get("confidence"),
                    "expected_move_pct": p.get("expected_move_pct"),
                }
                for p in preds[:6]
            ],
            "news": [
                {
                    "title": (n.get("title") or "")[:80],
                    "source": n.get("source"),
                    "impact": n.get("impact"),
                    "sentiment": round(float(n.get("sentiment_score", 0)), 3),
                }
                for n in news[:8]
            ],
            "context": context or {},
        }
        prompt = (
            "You are a senior stock-market analyst. Given verified quantitative data "
            "about one Indian stock, write a concise market-commentary paragraph (max 4 sentences). "
            "Explain the trend, momentum, key technical levels and risks, in simple language. "
            "Do NOT invent prices, financial figures or market events. Do not give a BUY/SELL/"
            "HOLD rating - describe the technical picture. Return only the commentary text.\n\n"
            f"Data: {json.dumps(data, default=str)}"
        )
        if self.ollama_available():
            try:
                text = ollama_client.generate(prompt, temperature=0.4, max_tokens=350)
                if text and len(text) > 30:
                    risks = self._risk_factors(text, rules)
                    return text.strip(), risks, "ollama"
            except Exception as exc:  # any failure -> rules fallback
                logger.warning("ollama analysis failed, using rule engine: %s", exc)
        summary = rules.get("summary") or "Analysis summary unavailable."
        return summary, rules.get("points", [])[:6], "rule_engine"

    def _risk_factors(self, ai_text: str, rules: Dict[str, Any]) -> List[str]:
        """Extract risk phrases from AI text; only generic risk labels (never prices)."""
        risk_words = ["high volatility", "overbought", "oversold", "drawdown", "resistance",
                      "support level", "low volume", "bearish", "caution", "rally"]
        out = []
        for line in ai_text.split("."):
            line = line.strip()
            if any(w in line.lower() for w in risk_words) and len(line) > 8 and len(out) < 5:
                out.append(line)
        return out or rules["points"][:5]

    # ------------------------------------------------------------------
    # Market summary (hourly / daily reports)
    # ------------------------------------------------------------------
    def market_summary(self, market_context: Dict[str, Any]) -> Dict[str, Any]:
        data = {
            "index_movements": market_context.get("index_movements", []),
            "top_performers": market_context.get("top_performers", []),
            "top_losers": market_context.get("top_losers", []),
            "top_sectors": market_context.get("top_sectors", []),
            "news_summaries": market_context.get("news_summaries", []),
            "risks": market_context.get("risks", []),
        }
        prompt = (
            "You are a senior equity analyst. Summarise the Indian stock market in 2-4 sentences. "
            "Do NOT invent numbers, prices or events; use only values from the data.\n"
            f"Data: {json.dumps(data, default=str)}"
        )
        if self.ollama_available():
            text = ollama_client.generate(prompt, temperature=0.35, max_tokens=400)
            if text and len(text) > 30:
                return {
                    "summary": text.strip(),
                    "data_source": "ollama",
                    "generated_at": datetime.utcnow().isoformat(),
                    "source_data": data,
                }
        # Deterministic rule-based summary of the market context.
        dirns = [d.get("direction", "") for d in market_context.get("index_movements", []) if isinstance(d, dict)]
        ups = sum(1 for d in dirns if "up" in str(d).lower() or "bullish" in str(d).lower())
        if not dirns:
            trend = "no index data available"
        elif ups == len(dirns):
            trend = "all advancing"
        elif ups == 0:
            trend = "all declining"
        else:
            trend = "mixed"
        raw_sectors = market_context.get("top_sectors", []) or []
        sector_names = [
            s.get("sector") if isinstance(s, dict) else str(s)
            for s in raw_sectors
        ]
        sector_names = [s for s in sector_names if s]
        summary = (
            f"Market overview: {len(dirns)} tracked indices — {trend}. "
            f"Sectors to watch: {', '.join(sector_names[:4]) or 'not available'}. "
            "Latest signals and news are in the terminal-style dashboard."
        )
        return {
            "summary": summary,
            "data_source": "rule_engine",
            "generated_at": datetime.utcnow().isoformat(),
            "source_data": data,
        }

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------
    def signal_for_stock(
        self,
        symbol: str,
        technical: Dict[str, Any],
        predictions: Optional[List[Dict[str, Any]]] = None,
        news_sentinel_score: float = 0.0,
        persist: bool = True,
    ) -> Signal:
        preds = predictions or []
        decision = rules_signal_for_stock(symbol, technical, preds, news_sentinel_score)
        summary = self._decision_summary(symbol, decision)
        ai_text, ai_risk, ai_source = self._ai_explain(
            symbol, technical, [], preds, {"signal": decision["signal_type"]},
            {"trend": technical.get("trend", "sideways"),
             "sentiment": 0.0,
             "risk_level": decision.get("risk_level", "medium"),
             "points": decision["reasons"],
             "summary": summary},
        )
        signal = make_signal_record(
            symbol=symbol,
            decision=decision,
            technical=technical,
            predictions=preds,
            news_sentinel_score=news_sentinel_norm(news_sentinel_score),
            ai_summary=ai_text[:500],
            ai_source=ai_source,
        )
        # The numeric levels always come from the quant ensemble; Ollama only
        # contributes the narrative when it is available.
        signal.ai_source = ai_source if ai_source == "ollama" else "quant_ensemble"
        if persist:
            db = SessionLocal()
            try:
                # Keep one live signal per symbol: refresh the latest row
                # instead of appending a new one on every click.
                existing = (
                    db.query(Signal)
                    .filter(Signal.symbol == symbol)
                    .order_by(Signal.generated_at.desc())
                    .first()
                )
                if existing is not None:
                    for attr in (
                        "signal_type", "confidence", "reasons", "entry_price",
                        "target_price", "stop_loss", "risk_reward",
                        "expected_holding_minutes", "tech_reasons", "fund_reasons",
                        "news_sentiment_score", "risk_level", "ai_summary",
                        "ai_source", "generated_at",
                    ):
                        setattr(existing, attr, getattr(signal, attr))
                    db.commit()
                    db.refresh(existing)
                    signal = existing
                else:
                    db.add(signal)
                    db.commit()
                    db.refresh(signal)
            finally:
                db.close()
        return signal

    @staticmethod
    def _decision_summary(symbol: str, decision: Dict[str, Any]) -> str:
        label = str(decision.get("signal_type", "HOLD")).replace("_", " ").title()
        entry = decision.get("entry_price")
        target = decision.get("target_price")
        stop = decision.get("stop_loss")
        rr = decision.get("risk_reward")
        conf = decision.get("confidence")
        parts = [f"{label} signal for {symbol}"]
        if entry:
            parts.append(f"entry ₹{float(entry):,.2f}")
        if target:
            parts.append(f"target ₹{float(target):,.2f}")
        if stop:
            parts.append(f"stop ₹{float(stop):,.2f}")
        if rr:
            parts.append(f"R:R {float(rr):.2f}")
        if conf is not None:
            parts.append(f"confidence {float(conf) * 100:.0f}%")
        head = " · ".join(parts) + "."
        reasons = decision.get("reasons") or []
        return head + (" " + " ".join(reasons[:2]) if reasons else "")


def news_sentinel_norm(x: float) -> float:
    try:
        return _clip(float(x))
    except (TypeError, ValueError):
        return 0.0


ai_service = AIService()
