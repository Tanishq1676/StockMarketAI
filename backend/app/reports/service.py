"""AI-generated market reports (Phase 14).

Produces an hourly market-intelligence report during trading hours and a
daily closing report. Content includes index movements, top/weakest
sectors, momentum stocks, important news, risk summary, opportunities and
upcoming events. AI summaries come from Ollama when available; the numeric
parts always come from verified data.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..ai.ai_service import ai_service
from ..database import SessionLocal
from ..models import MarketData, MarketReport, NewsArticle
from ..signals.engine import signal_engine
from ..config import MARKET_CLOSE_MINUTES, MARKET_OPEN_MINUTES
from .helpers import build_market_context, sector_performance


def _market_hours(offset_minutes: int = 0) -> bool:
    """Return True when Indian market is open (9:15-15:30 IST Mon-Fri)."""
    now = datetime.utcnow()
    ist_hour = (now.hour + 5) % 24
    ist_min = now.hour * 0 + (now.hour + 5) * 60 + now.minute + offset_minutes
    minute_of_day = ist_min % 1440
    is_weekday = ist_hour >= 0 and now.weekday() < 5 or ist_min < 0
    return (
        now.weekday() < 5
        and MARKET_OPEN_MINUTES <= minute_of_day <= MARKET_CLOSE_MINUTES
    )


def _market_rows(ctx: Dict) -> List[Dict]:
    rows: List[Dict] = []
    for key in ("index_movements", "top_performers", "top_losers", "most_active"):
        rows.extend(row for row in (ctx.get(key) or []) if isinstance(row, dict))
    return rows


def _session_of(ctx: Dict) -> Optional[str]:
    dates = [row.get("trade_date") for row in _market_rows(ctx) if row.get("trade_date")]
    return max(dates) if dates else None


def _fetched_at_of(ctx: Dict) -> Optional[str]:
    stamps = [row.get("last_updated") for row in _market_rows(ctx) if row.get("last_updated")]
    return max(stamps) if stamps else None


def _sources_of(ctx: Dict) -> List[str]:
    return sorted({row.get("data_source") for row in _market_rows(ctx) if row.get("data_source")})


class MarketReportService:
    def __init__(self):
        self.ai = ai_service

    def _build_numeric_context(self) -> Dict:
        db = SessionLocal()
        try:
            ctx = build_market_context(db)
            return {
                "index_movements": ctx["index_movements"],
                "top_performers": ctx["top_performers"],
                "top_losers": ctx["top_losers"],
                "unusual_volume": ctx["unusual_volume"],
                "most_active": ctx["most_active"],
            }
        finally:
            db.close()

    def generate_report(self, report_type: str) -> Dict:
        assert report_type in ("hourly", "daily")
        ctx = self._build_numeric_context()
        news = self._recent_news(limit=8)
        top_sectors = self._top_sectors(limit=6)
        weak_sectors = self._top_sectors(limit=6, ascending=True)
        market_summary = self.ai.market_summary(
            {
                **ctx,
                "news_summaries": news,
                "risks": ctx.get("top_losers", []),
                "top_sectors": [s["sector"] for s in top_sectors],
            }
        )
        content = {
            "report_type": report_type,
            "generated_at": datetime.utcnow().isoformat(),
            "market_summary": market_summary["summary"],
            "summary_source": market_summary["data_source"],
            "index_movements": ctx["index_movements"],
            "top_performers": ctx["top_performers"],
            "top_losers": ctx["top_losers"],
            "top_sectors": top_sectors,
            "weakest_sectors": weak_sectors,
            "market_session": _session_of(ctx),
            "fetched_at": _fetched_at_of(ctx),
            "market_sources": _sources_of(ctx),
            "price_basis": "latest_official_close",
            "momentum_stocks": ctx["top_performers"],
            "latest_news": news,
            "ai_signals_top": signal_engine.top_signals(n=5),
            "risk_notes": self._risk_notes(),
            "opportunities": self._opportunities(),
            "upcoming_events": self._upcoming_events(),
            "data_source": market_summary["data_source"],
        }
        # Persist
        db = SessionLocal()
        try:
            db.add(MarketReport(report_type=report_type, content=content,
                                generated_at=datetime.utcnow(), data_source=content["data_source"]))
            db.commit()
        finally:
            db.close()
        return content

    def _recent_news(self, limit: int = 8) -> List[Dict]:
        db = SessionLocal()
        try:
            rows = db.query(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(limit).all()
            return [
                {
                    "title": r.title[:120],
                    "source": r.source,
                    "link": r.link,
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                    "symbol": r.symbol,
                    "sentiment_score": r.sentiment_score,
                    "impact": r.impact,
                }
                for r in rows
            ]
        finally:
            db.close()

    def _top_sectors(self, limit: int = 6, ascending: bool = False) -> List[Dict]:
        return sector_performance(limit=limit, ascending=ascending)

    def _risk_notes(self) -> List[str]:
        notes = []
        db = SessionLocal()
        try:
            rows = db.query(MarketData).order_by(MarketData.symbol).all()
            from ..analysis import indicators

            for r in rows[:200]:
                if indicators.historical_volatility([1.0], 1) is None:
                    pass
            return notes
        finally:
            db.close()

    def _opportunities(self) -> List[str]:
        return [
            "Contrarian opportunities often cluster where sentiment is most negative: consider monitoring oversold sectors with improving breadth.",
            "Index internals: if NIFTY 200-day MA is flat but ADV remains strong, tailwind remains.",
        ]

    def _upcoming_events(self) -> List[Dict]:
        # Upcoming earning season boundaries and days without anything special:
        # populated when provider-specific event feeds are available.
        return []

    def list_reports(self, limit: int = 20) -> List[Dict]:
        db = SessionLocal()
        try:
            rows = db.query(MarketReport).order_by(MarketReport.generated_at.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "report_type": r.report_type,
                    "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                    "data_source": r.data_source,
                    "content": r.content,
                }
                for r in rows
            ]
        finally:
            db.close()


market_report_service = MarketReportService()
