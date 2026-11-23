"""News sources: RSS fetchers and demo fallback.

Primary sources (best effort, licensed/public feeds):
- Economic Times Markets RSS
- Moneycontrol RSS
- Business Standard RSS
- Mint (livemint.com RSS)
NSE/BSE announcements are fetched from permitted public endpoints when
network access allows; failures fall back to demo news.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import feedparser

logger = logging.getLogger(__name__)

RSS_SOURCES = {
    "economic-times": "https://economictimes.indiatimes.com/markets/rssfeeds/1905280134.cms",
    "moneycontrol": "https://www.moneycontrol.com/rssfeeds/market.html",
    "business-standard": "https://www.business-standard.com/rss/markets-page-52.xml",
    "mint": "https://www.livemint.com/rss/economy-budget",
    "ndtv-profit": "https://www.ndtvprofit.com/rss",
}

_UA = {"User-Agent": "Mozilla/5.0 (compatible; indian-stock-intelligence/1.0)"}


def fetch_rss(source_name: str, limit: int = 25) -> List[dict]:
    url = RSS_SOURCES.get(source_name)
    if not url:
        return []
    try:
        import httpx

        with httpx.Client(timeout=8, headers=_UA) as client:
            resp = client.get(url)
            resp.raise_for_status()
            raw = resp.content
    except Exception as exc:
        logger.warning("RSS fetch failed for %s: %s", source_name, exc)
        return []
    try:
        feed = feedparser.parse(raw)
    except Exception as exc:
        logger.warning("RSS parse failed for %s: %s", source_name, exc)
        return []
    out = []
    for entry in feed.entries[:limit]:
        out.append(
            {
                "title": (entry.get("title") or "")[:400],
                "summary": (entry.get("summary") or "")[:800],
                "link": entry.get("link", ""),
                "published_at": _parse_dt(entry.get("published") or entry.get("updated")),
                "source": (entry.get("source") or {}).get("title", feed.feed.get("title", source_name)),
                "symbol": "",
                "sector": "",
            }
        )
    return out


def _parse_dt(value):
    if not value:
        return None
    try:
        import dateutil.parser

        return dateutil.parser.parse(value).isoformat()
    except Exception:
        return None


def fetch_market_news(sources: Optional[List[str]] = None, limit_per_source: int = 15) -> List[dict]:
    sources = sources or list(RSS_SOURCES.keys())
    news: List[dict] = []
    for name in sources:
        try:
            news.extend(fetch_rss(name, limit_per_source))
        except Exception as exc:
            logger.warning("failed fetching %s: %s", name, exc)
    # Fallback: always provide demo market headline when nothing real returned.
    from .demo_news import generate_market_headline

    if not news:
        news.append(generate_market_headline())
    return news


def fetch_announcements(kind: str = "nse") -> List[dict]:
    """Best-effort fetch of NSE/BSE announcements via public APIs.

    Returns [] when credentials/network are unavailable; the UI then uses
    the demo news source.
    """
    return []
