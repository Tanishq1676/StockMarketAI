"""Dashboard service (Phase 11): composes market snapshot + AI summary + news."""

from __future__ import annotations

from typing import Dict

from ..ai.ai_service import ai_service
from ..alerts.service import alerts_service
from ..news.service import news_service
from ..portfolio.calculator import portfolio_service
from ..signals.engine import signal_engine
from ..database import SessionLocal
from ..models import IndexMeta, MarketData
from ..reports.helpers import build_market_context, sector_performance

INDEX_SYMBOLS = ["NIFTY50", "NIFTYNEXT50", "NIFTY100", "NIFTY500", "BANKNIFTY", "SENSEX", "BSE100"]


OFFICIAL_SOURCES = ("nse", "bse", "nse-index", "bse-index", "nse-live")


def _fmt(r):
    return {
        "symbol": r.symbol,
        "name": r.name,
        "price": round(float(r.price_close), 2),
        "change_pct": round(float(r.change_pct or 0.0), 3),
        "prev_close": round(float(r.prev_close), 2) if r.prev_close is not None else None,
        "volume": int(r.volume or 0),
        "trade_date": r.trade_date,
        "last_updated": (r.fetched_at or r.last_updated).isoformat() if (r.fetched_at or r.last_updated) else None,
        "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
        "data_source": r.data_source,
        "is_live": bool(r.is_live),
        "delay_minutes": int(r.delay_minutes or 0),
    }


def index_snapshot() -> Dict[str, list]:
    db = SessionLocal()
    try:
        rows = (
            db.query(MarketData)
            .filter(
                MarketData.symbol.in_(INDEX_SYMBOLS),
                MarketData.data_source.in_(OFFICIAL_SOURCES),
            )
            .all()
        )
        idx_names = {i.symbol: i.name for i in db.query(IndexMeta).all()}
        out = []
        for r in rows:
            out.append({
                "symbol": r.symbol,
                "name": idx_names.get(r.symbol, r.symbol),
                "price": round(float(r.price_close), 2),
                "change_pct": round(float(r.change_pct or 0.0), 3),
                "prev_close": round(float(r.prev_close), 2) if r.prev_close is not None else None,
                "volume": int(r.volume or 0),
                "trade_date": r.trade_date,
                "last_updated": (r.fetched_at or r.last_updated).isoformat() if (r.fetched_at or r.last_updated) else None,
                "data_source": r.data_source,
                "is_live": bool(r.is_live),
                "delay_minutes": int(r.delay_minutes or 0),
            })
        out.sort(key=lambda d: -abs(d["change_pct"] or 0))
        return {"indices": out, "updated_at": _now_iso()}
    finally:
        db.close()


def _now_iso():
    from datetime import datetime

    return datetime.utcnow().isoformat()


def compose_dashboard() -> Dict:
    ctx = build_market_context()
    portfolio = portfolio_service.portfolio_summary()
    news = news_service.latest_news(limit=10)
    sectors = sector_performance(limit=4)
    summary = ai_service.market_summary(
        {
            "index_movements": ctx["index_movements"],
            "top_performers": ctx["top_performers"],
            "top_losers": ctx["top_losers"],
            "unusual_volume": ctx["unusual_volume"],
            "top_sectors": [s["sector"] for s in sectors],
            "news_summaries": [n["title"] for n in news[:6]],
            "risks": [
                {"symbol": s["symbol"], "reason": "high volatility" if abs(s["change_pct"] or 0) > 4 else "large move"}
                for s in ctx["top_losers"][:5]
            ],
        }
    )
    return {
        "snapshot": {
            "indices": index_snapshot()["indices"],
            "top_gainers": ctx["top_performers"],
            "top_losers": ctx["top_losers"],
            "most_active": ctx["most_active"],
            "unusual_volume": ctx["unusual_volume"],
            "sectors": sectors,
            "updated_at": _now_iso(),
            "data_status": data_status(),
        },
        "ai_market_summary": summary["summary"],
        "ai_summary_source": summary["data_source"],
        "latest_news": news,
        "top_signals": signal_engine.top_signals(n=10),
        "alert_notifications": alerts_service.notifications(limit=10),
        "portfolio_summary": portfolio,
    }


def data_status() -> Dict:
    """Latest official session + ingest timestamp shown on the dashboard."""
    db = SessionLocal()
    try:
        latest = (
            db.query(MarketData)
            .filter(MarketData.data_source.in_(OFFICIAL_SOURCES))
            .order_by(MarketData.trade_date.desc(), MarketData.fetched_at.desc())
            .first()
        )
        sources = sorted(
            {
                r.data_source
                for r in db.query(MarketData).all()
                if r.data_source in OFFICIAL_SOURCES
            }
        )
        return {
            "latest_trade_date": latest.trade_date if latest else None,
            "fetched_at": latest.fetched_at.isoformat() if latest and latest.fetched_at else None,
            "sources": sources,
            "is_live": bool(latest.is_live) if latest else False,
            "delay_minutes": int(latest.delay_minutes or 0) if latest else 0,
        }
    finally:
        db.close()
