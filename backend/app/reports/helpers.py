"""Helpers shared by dashboard/report builders."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func

from ..database import SessionLocal
from ..models import HistoricalPrice, IndexMeta, MarketData, StockMeta

OFFICIAL_SOURCES = ("nse", "bse", "nse-index", "bse-index", "nse-live")
MAJOR_INDICES = {"NIFTY50", "NIFTYNEXT50", "NIFTY100", "NIFTY500", "BANKNIFTY", "SENSEX"}

_SECTOR_CACHE: Dict[str, object] = {"at": None, "averages": None}


def sector_performance(limit: int = 6, ascending: bool = False) -> List[Dict]:
    """Average 60-session return per sector from stored official history.

    One grouped read is used instead of a query per symbol, and a short
    in-process cache keeps repeated dashboard/report builds fast.
    """
    from ..data import catalog

    now = datetime.utcnow()
    cached_at = _SECTOR_CACHE.get("at")
    averages = _SECTOR_CACHE.get("averages")
    fresh = (
        isinstance(cached_at, datetime)
        and isinstance(averages, dict)
        and (now - cached_at).total_seconds() < 600
    )
    if not fresh:
        start = (now - timedelta(days=90)).strftime("%Y-%m-%d")
        db = SessionLocal()
        try:
            rows = (
                db.query(HistoricalPrice.symbol, HistoricalPrice.close)
                .filter(
                    HistoricalPrice.source == "nse",
                    HistoricalPrice.date >= start,
                )
                .order_by(HistoricalPrice.symbol, HistoricalPrice.date)
                .all()
            )
        finally:
            db.close()
        series: Dict[str, List[float]] = {}
        for symbol, close in rows:
            series.setdefault(symbol, []).append(float(close))
        sector_of = {
            s["symbol"]: (s.get("sector") or "other")
            for s in catalog.get_stocks()
        }
        totals: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for symbol, closes in series.items():
            if len(closes) < 3 or not closes[0]:
                continue
            pct = (closes[-1] - closes[0]) / closes[0] * 100.0
            sector = sector_of.get(symbol, "other")
            totals[sector] = totals.get(sector, 0.0) + pct
            counts[sector] = counts.get(sector, 0) + 1
        averages = {sector: totals[sector] / counts[sector] for sector in totals if counts[sector]}
        _SECTOR_CACHE.update({"at": now, "averages": averages})
    ordered = sorted(averages.items(), key=lambda kv: kv[1], reverse=not ascending)
    return [{"sector": k, "avg_pct_60d": round(v, 3)} for k, v in ordered[:limit]]


def _row_dict(r: MarketData) -> Dict:
    return {
        "symbol": r.symbol,
        "price": round(float(r.price_close), 2),
        "change_pct": round(float(r.change_pct or 0.0), 3),
        "prev_close": round(float(r.prev_close), 2) if r.prev_close is not None else None,
        "volume": int(r.volume or 0),
        "trade_date": r.trade_date,
        "last_updated": (r.fetched_at or r.last_updated).isoformat() if (r.fetched_at or r.last_updated) else None,
        "data_source": r.data_source,
        "is_live": bool(r.is_live),
        "delay_minutes": int(r.delay_minutes or 0),
    }


def _rows_to_dicts(rows, source_key="symbol") -> List[Dict]:
    return [_row_dict(r) for r in rows]


def build_market_context(db=None) -> Dict:
    """Top gainers/losers/active + per-index movements from official MarketData."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        stock_symbols = {
            m.symbol
            for m in db.query(StockMeta).filter(StockMeta.status == "active").all()
        }
        index_names = {m.symbol: m.name for m in db.query(IndexMeta).all()}
        rows = (
            db.query(MarketData)
            .filter(MarketData.data_source.in_(OFFICIAL_SOURCES))
            .all()
        )
        data = [_row_dict(r) for r in rows]
        stocks = [d for d in data if d["symbol"] in stock_symbols]
        index_movements = [
            {
                "symbol": d["symbol"],
                "name": index_names.get(d["symbol"], d["symbol"]),
                "price": d["price"],
                "change_pct": d["change_pct"],
                "prev_close": d["prev_close"],
                "direction": "up" if d["change_pct"] > 0 else ("down" if d["change_pct"] < 0 else "flat"),
                "trade_date": d["trade_date"],
                "last_updated": d["last_updated"],
                "data_source": d["data_source"],
                "is_live": d["is_live"],
                "delay_minutes": d["delay_minutes"],
            }
            for d in data
            if d["symbol"] in MAJOR_INDICES and d["symbol"] in index_names
        ]
        top_performers = sorted(stocks, key=lambda d: -d["change_pct"])[:10]
        top_losers = sorted(stocks, key=lambda d: d["change_pct"])[:10]
        most_active = sorted(stocks, key=lambda d: -d["volume"])[:10]

        latest_session = max((d["trade_date"] for d in stocks if d.get("trade_date")), default=None)
        volume_avg: Dict[str, float] = {}
        if latest_session:
            cutoff = (date.fromisoformat(latest_session) - timedelta(days=120)).isoformat()
            avg_rows = (
                db.query(HistoricalPrice.symbol, func.avg(HistoricalPrice.volume))
                .filter(
                    HistoricalPrice.source == "nse",
                    HistoricalPrice.date >= cutoff,
                    HistoricalPrice.date < latest_session,
                )
                .group_by(HistoricalPrice.symbol)
                .all()
            )
            volume_avg = {sym: float(avg or 0.0) for sym, avg in avg_rows}
        for d in stocks:
            avg = volume_avg.get(d["symbol"], 0.0)
            d["volume_ratio"] = round(d["volume"] / avg, 2) if avg > 0 else None
        unusual_volume = sorted(
            [d for d in stocks if (d.get("volume_ratio") or 0) >= 1.5],
            key=lambda d: -d["volume_ratio"],
        )[:8]
        return {
            "index_movements": index_movements,
            "top_performers": top_performers,
            "top_losers": top_losers,
            "most_active": most_active,
            "unusual_volume": unusual_volume,
            "all": data,
        }
    finally:
        if close_db:
            db.close()
