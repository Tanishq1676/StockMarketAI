"""News endpoints (Phase 6)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..news.service import news_service

router = APIRouter()


@router.get("/news", tags=["news"])
def latest_news(limit: int = Query(20, ge=1, le=100), symbol: str = "", sector: str = ""):
    rows = news_service.latest_news(limit=limit, symbol=symbol or None, sector=sector or None)
    return {"news": rows, "count": len(rows), "data_source": rows[0]["analysis_source"] if rows else "none"}


@router.get("/news/symbol/{symbol}", tags=["news"])
def news_for_symbol(symbol: str, limit: int = Query(10, ge=1, le=50)):
    return {"symbol": symbol, "news": news_service.news_for_symbol(symbol.upper(), limit=limit)}


@router.get("/news/sector/{sector}", tags=["news"])
def news_by_sector(sector: str, limit: int = Query(20, ge=1, le=50)):
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        from ..models import NewsArticle

        rows = db.query(NewsArticle).filter(NewsArticle.sector == sector).order_by(NewsArticle.published_at.desc()).limit(limit).all()
        return {"sector": sector, "news": [news_service._to_dict(r) for r in rows]}
    finally:
        db.close()
