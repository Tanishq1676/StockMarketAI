"""Stocks + indices endpoints (Phases 2, 3)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..ai.ai_service import ai_service
from ..analysis.time_series import fetch_history, time_series_report
from ..data import catalog, providers
from ..database import SessionLocal
from ..models import IndexMeta, IngestRun, MarketData, StockMeta

router = APIRouter()

OFFICIAL_SOURCES = ("nse", "bse", "nse-index", "bse-index", "nse-live")


def _quote_dict(q: providers.Quote) -> dict:
    return {
        "symbol": q.symbol,
        "name": q.name,
        "open": q.open,
        "high": q.high,
        "low": q.low,
        "close": q.close,
        "prev_close": q.prev_close,
        "volume": q.volume,
        "change_pct": q.change_pct,
        "last_updated": q.last_updated,
        "fetched_at": q.fetched_at or q.last_updated,
        "trade_date": q.trade_date,
        "data_source": q.source,
        "is_live": q.is_live,
        "delay_minutes": q.delay_minutes,
        "source_url": q.source_url,
    }


def _hist_dicts(rows):
    return [
        {"date": r.date, "open": r.open, "high": r.high, "low": r.low, "close": r.close,
         "volume": r.volume, "source": getattr(r, "source", "unknown")}
        for r in rows
    ]


def _row_dict(r: MarketData) -> dict:
    return {
        "price": round(float(r.price_close), 2),
        "open": round(float(r.price_open), 2),
        "high": round(float(r.price_high), 2),
        "low": round(float(r.price_low), 2),
        "prev_close": round(float(r.prev_close), 2) if r.prev_close is not None else None,
        "change_pct": round(float(r.change_pct or 0.0), 3),
        "volume": int(r.volume or 0),
        "trade_date": r.trade_date,
        "last_updated": (r.fetched_at or r.last_updated).isoformat() if (r.fetched_at or r.last_updated) else None,
        "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
        "data_source": r.data_source,
        "is_live": bool(r.is_live),
        "delay_minutes": int(r.delay_minutes or 0),
        "source_url": r.source_url,
    }


@router.get("/stocks", tags=["stocks"])
def list_stocks(limit: int = 500, source: Optional[str] = None, symbols: Optional[str] = None):
    db = SessionLocal()
    try:
        query = db.query(StockMeta).filter(StockMeta.status == "active")
        wanted = [s.strip().upper() for s in (symbols or "").split(",") if s.strip()]
        if wanted:
            query = query.filter(StockMeta.symbol.in_(wanted))
        metas = query.order_by(StockMeta.symbol).all()
        symbols = [m.symbol for m in metas]
        quotes = {
            r.symbol: r
            for r in db.query(MarketData).filter(
                MarketData.symbol.in_(symbols), MarketData.data_source.in_(OFFICIAL_SOURCES)
            ).all()
        } if symbols else {}
        out = []
        for m in metas[:limit]:
            r = quotes.get(m.symbol)
            if r is not None:
                row = _row_dict(r)
                out.append(
                    {
                        "symbol": m.symbol,
                        "name": m.name,
                        "exchange": m.exchange,
                        "sector": m.sector,
                        "market_cap": m.market_cap,
                        "nse_indices": m.nse_indices or [],
                        "isin": m.isin,
                        "bse_symbol": m.bse_symbol,
                        **row,
                    }
                )
                continue
            q = None
            try:
                q = providers.get_quote(m.symbol, preferred=source)
            except providers.ProviderUnavailable:
                q = None
            out.append(
                {
                    "symbol": m.symbol,
                    "name": m.name,
                    "exchange": m.exchange,
                    "sector": m.sector,
                    "market_cap": m.market_cap,
                    "nse_indices": m.nse_indices or [],
                    "isin": m.isin,
                    "bse_symbol": m.bse_symbol,
                    "price": q.close if q else None,
                    "change_pct": round(q.change_pct, 3) if q else None,
                    "trade_date": q.trade_date if q else None,
                    "last_updated": q.last_updated if q else None,
                    "data_source": q.source if q else "unavailable",
                    "is_live": q.is_live if q else False,
                    "delay_minutes": q.delay_minutes if q else 0,
                }
            )
        return {
            "stocks": out,
            "count": len(out),
            "data_source": out[0]["data_source"] if out else "n/a",
            "latest_trade_date": max((o.get("trade_date") or "" for o in out), default=None) or None,
        }
    finally:
        db.close()


@router.get("/search", tags=["stocks"])
def search_stocks(q: str = Query("", min_length=0), limit: int = 20):
    results = catalog.search_stocks(q, limit)
    return {"results": results, "query": q}


@router.get("/stocks/{symbol}", tags=["stocks"])
def get_stock_detail(symbol: str, history_days: int = 5 * 252):
    from types import SimpleNamespace

    symbol = symbol.upper()
    db = SessionLocal()
    try:
        meta = db.query(StockMeta).filter(StockMeta.symbol == symbol).first()
        is_index = False
        if not meta:
            idx = db.query(IndexMeta).filter(IndexMeta.symbol == symbol).first()
            if idx:
                meta = SimpleNamespace(
                    symbol=idx.symbol, bse_symbol="", name=idx.name,
                    exchange=idx.exchange, sector="", market_cap="",
                    nse_indices=[], data_source=idx.data_source,
                    status="active", type=idx.type,
                )
                is_index = True
        if not meta:
            raise HTTPException(status_code=404, detail=f"{symbol} not found")
        if not is_index and getattr(meta, "status", "active") != "active":
            raise HTTPException(status_code=404, detail=f"{symbol} is not part of the active universe")
        try:
            quote = providers.get_quote(meta.symbol)
        except providers.ProviderUnavailable:
            quote = None
        history = fetch_history(
            meta.symbol,
            (date.today() - timedelta(days=history_days)).strftime("%Y-%m-%d"),
            date.today().strftime("%Y-%m-%d"),
        )
        analysis = time_series_report(meta.symbol, days=history_days)
        if is_index:
            analysis = {
                "symbol": meta.symbol,
                "data_source": quote.source if quote else "unavailable",
                "days_of_history": len(history),
                "closes": [h.close for h in history][-700:],
                "dates": [h.date for h in history][-700:],
                "opens": [h.open for h in history][-700:],
                "highs": [h.high for h in history][-700:],
                "lows": [h.low for h in history][-700:],
                "volumes": [h.volume for h in history][-700:],
                "trend": (analysis.get("trend") if isinstance(analysis, dict) else None) or "sideways",
                "ai_source": "rule_engine",
                "ai_summary": f"Index {meta.name} — tracked from {quote.source if quote else 'official'} data.",
                "ai_risk_factors": [],
                "sentiment_score": 0.0,
                "news": [],
            }
        prev_close = quote.prev_close if quote else None
        if prev_close is None and len(history) >= 2:
            prev_close = history[-2].close
        quote_payload = _quote_dict(quote) if quote else None
        if quote_payload is not None:
            quote_payload["prev_close"] = prev_close
        return {
            "meta": {
                "symbol": meta.symbol,
                "bse_symbol": getattr(meta, "bse_symbol", "") or "",
                "name": meta.name,
                "exchange": meta.exchange,
                "sector": getattr(meta, "sector", "") or "",
                "market_cap": getattr(meta, "market_cap", "") or "",
                "nse_indices": getattr(meta, "nse_indices", None) or [],
                "data_source": meta.data_source,
                "status": meta.status,
                **({"type": getattr(meta, "type", "market_index")} if is_index else {}),
            },
            "quote": quote_payload,
            "history": _hist_dicts(history[-700:]),
            "history_length": len(history),
            "analysis": analysis,
        }
    finally:
        db.close()


@router.get("/indices", tags=["indices"])
def list_indices():
    db = SessionLocal()
    try:
        rows = db.query(IndexMeta).order_by(IndexMeta.type, IndexMeta.symbol).all()
        market = {
            r.symbol: r
            for r in db.query(MarketData).filter(
                MarketData.symbol.in_([m.symbol for m in rows]),
                MarketData.data_source.in_(OFFICIAL_SOURCES),
            ).all()
        }
        out = []
        for m in rows:
            md = market.get(m.symbol)
            if md is None:
                continue
            out.append(
                {
                    "symbol": m.symbol,
                    "name": m.name,
                    "type": m.type,
                    "exchange": m.exchange,
                    "price": round(md.price_close, 2),
                    "change_pct": round(float(md.change_pct or 0.0), 3),
                    "prev_close": round(float(md.prev_close), 2) if md.prev_close is not None else None,
                    "trade_date": md.trade_date,
                    "data_source": md.data_source,
                    "is_live": bool(md.is_live),
                    "delay_minutes": int(md.delay_minutes or 0),
                    "last_updated": (md.fetched_at or md.last_updated).isoformat() if (md.fetched_at or md.last_updated) else None,
                }
            )
        return {
            "indices": out,
            "count": len(out),
            "latest_trade_date": max((o.get("trade_date") or "" for o in out), default=None) or None,
        }
    finally:
        db.close()


@router.get("/indices/{symbol}/history", tags=["indices"])
def index_history(symbol: str, days: int = 5 * 252):
    start = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = fetch_history(symbol.upper(), start, date.today().strftime("%Y-%m-%d"))
    return {"symbol": symbol, "history": _hist_dicts(rows)}


@router.get("/market/data-status", tags=["market"])
def market_data_status():
    """What official data is loaded, its latest session and ingest time."""
    from ..data import ingest

    report = ingest.coverage_report()
    db = SessionLocal()
    try:
        latest_run = db.query(IngestRun).order_by(IngestRun.started_at.desc()).first()
        report["last_ingest"] = {
            "job": latest_run.job,
            "status": latest_run.status,
            "started_at": latest_run.started_at.isoformat() if latest_run.started_at else None,
            "finished_at": latest_run.finished_at.isoformat() if latest_run.finished_at else None,
            "rows_fetched": latest_run.rows_fetched,
            "rows_inserted": latest_run.rows_inserted,
            "latest_trade_date": latest_run.latest_trade_date,
        } if latest_run else None
    finally:
        db.close()
    return report


@router.get("/ai/analysis/{symbol}", tags=["ai"])
def ai_analysis(symbol: str):
    """AI natural-language analysis of a stock (rule engine + Ollama)."""
    analysis = time_series_report(symbol, days=5 * 252)
    predictions = _predictions_for_symbol(symbol)
    result = ai_service.analyze_stock(symbol, analysis, predictions=predictions)
    result["data_source"] = analysis.get("data_source")
    return result


def _predictions_for_symbol(symbol: str):
    from ..database import SessionLocal as SL

    from ..models import Prediction

    db = SL()
    try:
        rows = db.query(Prediction).filter(Prediction.symbol == symbol).order_by(Prediction.generated_at.desc()).limit(6).all()
        return [
            {
                "horizon": {"15min": 15, "30min": 30, "1hour": 60, "2hour": 120, "1day": 1440, "5days": 3600}.get(
                    _h(r.horizon_minutes), r.horizon_minutes
                ),
                "predicted_close": r.predicted_close,
                "direction": r.direction,
                "confidence": r.confidence,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                "data_source": "predictions",
            }
            for r in rows
        ]
    finally:
        db.close()


def _h(minutes: int) -> str:
    m = {15: "15min", 30: "30min", 60: "1hour", 120: "2hour", 1440: "1day", 3600: "5days"}
    return m.get(minutes, str(minutes))
