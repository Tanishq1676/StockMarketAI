"""News service: fetch, classify, dedupe, persist and query financial news."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..data import catalog
from ..database import SessionLocal
from ..models import NewsArticle
from . import demo_news, sentiment, sources

logger = logging.getLogger(__name__)


def classify_news(news_item: Dict) -> Dict:
    """Attach sentiment/impact/affected-entity classification to a raw item."""
    text = f"{news_item.get('title', '')} {news_item.get('summary', '')}"
    score = sentiment.score_text(text)
    impact = sentiment.classify_impact(score)
    symbol = _extract_symbol(news_item.get("symbol", "") or "", news_item.get("title", "") + news_item.get("summary", ""))
    sector = _extract_sector(symbol) or news_item.get("sector", "")
    return {
        "title": news_item.get("title", ""),
        "source": news_item.get("source", ""),
        "link": news_item.get("link", ""),
        "summary": (news_item.get("summary") or "")[:900],
        "published_at": news_item.get("published_at") or datetime.utcnow().isoformat(),
        "symbol": symbol,
        "sector": sector,
        "sentiment_score": round(score, 3),
        "impact": impact,
        "analysis_source": news_item.get("analysis_source", "sentiment_analysis"),
    }


def _extract_symbol(explicit: str, text: str) -> str:
    if explicit:
        return explicit
    # Match full NSE symbols in the text (e.g. "TCS", "INFY")
    import re

    for stock in catalog.get_stocks():
        sym = stock["symbol"]
        if re.search(rf"\b{re.escape(sym)}\b", text, re.IGNORECASE):
            return sym
    return ""


def _extract_sector(symbol: str) -> str:
    for stock in catalog.get_stocks():
        if stock["symbol"] == symbol:
            return stock.get("sector", "")
    return ""


class NewsService:
    def __init__(self, sources_to_use: Optional[List[str]] = None):
        self.sources_to_use = sources_to_use

    def fetch_and_store(self, limit_per_source: int = 12, store: bool = True) -> List[Dict]:
        raw = sources.fetch_market_news(self.sources_to_use, limit_per_source)
        classified = [classify_news(r) for r in raw]
        classified = [c for c in classified if c.get("link")]
        if store:
            self.store_articles(classified)
        return classified

    def store_articles(self, articles: List[Dict]) -> int:
        db = SessionLocal()
        try:
            existing = {r[0] for r in db.query(NewsArticle.link).all()}
            added = 0
            for a in articles:
                if not a.get("link") or a["link"] in existing:
                    continue  # dedupe by link
                db.add(
                    NewsArticle(
                        title=a.get("title", ""),
                        source=a.get("source", ""),
                        link=a["link"],
                        summary=a.get("summary", ""),
                        published_at=datetime.fromisoformat(a["published_at"]) if a.get("published_at") else datetime.utcnow(),
                        symbol=a.get("symbol", ""),
                        sector=a.get("sector", ""),
                        sentiment_score=a.get("sentiment_score", 0.0),
                        impact=a.get("impact", "neutral"),
                        analysis_source=a.get("analysis_source", "sentiment_analysis"),
                    )
                )
                existing.add(a["link"])
                added += 1
            db.commit()
            return added
        finally:
            db.close()

    def latest_news(self, limit: int = 30, symbol: Optional[str] = None, sector: Optional[str] = None) -> List[Dict]:
        db = SessionLocal()
        try:
            q = db.query(NewsArticle).order_by(NewsArticle.published_at.desc())
            if symbol:
                q = q.filter(NewsArticle.symbol == symbol)
            if sector:
                q = q.filter(NewsArticle.sector == sector)
            return [self._to_dict(r) for r in q.limit(limit).all()]
        finally:
            db.close()

    def news_for_symbol(self, symbol: str, limit: int = 10) -> List[Dict]:
        return self.latest_news(limit=limit, symbol=symbol)

    def _to_dict(self, r: NewsArticle) -> Dict:
        return {
            "title": r.title,
            "source": r.source,
            "link": r.link,
            "summary": r.summary,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "symbol": r.symbol,
            "sector": r.sector,
            "sentiment_score": r.sentiment_score,
            "impact": r.impact,
            "analysis_source": r.analysis_source,
        }


news_service = NewsService()
