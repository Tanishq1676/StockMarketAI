"""FastAPI application (Phase 1+2..16). Compose of modular routers."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import database
from .config import settings
from .database import init_db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")


def seed_master_data() -> None:
    """Align StockMeta and IndexMeta tables with the master catalog."""
    from .data import catalog
    from .models import IndexMeta, StockMeta

    db = database.SessionLocal()
    try:
        catalog_symbols = {s["symbol"] for s in catalog.get_stocks()}
        existing = {r.symbol: r for r in db.query(StockMeta).all()}
        for s in catalog.get_stocks():
            meta = existing.get(s["symbol"])
            if meta is None:
                meta = StockMeta(symbol=s["symbol"], exchange=s.get("exchange", "NSE"))
                db.add(meta)
                existing[s["symbol"]] = meta
            meta.symbol = s["symbol"]
            meta.exchange = s.get("exchange", "NSE")
            meta.name = s["name"]
            meta.sector = s.get("sector", "")
            meta.market_cap = s.get("cap", "")
            meta.nse_indices = s.get("indices", [])
            if s.get("isin"):
                meta.isin = s["isin"]
            meta.status = "active"
        for symbol, meta in existing.items():
            if symbol not in catalog_symbols and meta.status == "active":
                meta.status = "inactive"
        existing_idx = {r.symbol: r for r in db.query(IndexMeta).all()}
        for i in catalog.get_all_indices():
            meta = existing_idx.get(i["symbol"])
            if meta is None:
                meta = IndexMeta(symbol=i["symbol"], name=i["name"], type=i.get("type", "market_index"), exchange=i.get("exchange", "NSE"))
                db.add(meta)
                existing_idx[i["symbol"]] = meta
            meta.name = i["name"]
            meta.type = i.get("type", "market_index")
            meta.exchange = i.get("exchange", "NSE")
        db.commit()
        logger.info("seeded %d stocks and %d indices", len(catalog.get_stocks()), len(catalog.get_all_indices()))
    except Exception as exc:  # pragma: no cover
        logger.warning("seed failed: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("initialising database at %s", settings.database_url)
    init_db()
    seed_master_data()
    # start scheduler (APScheduler or asyncio fallback)
    from .scheduler import MarketScheduler

    scheduler = MarketScheduler()
    try:
        scheduler.start()
    except Exception as exc:
        logger.warning("scheduler failed to start: %s", exc)
    app.state.scheduler = scheduler
    logger.info("AI market intelligence platform started (sources: %s)", settings.list_sources() if hasattr(settings, 'list_sources') else settings.database_url)
    yield
    try:
        scheduler.stop()
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="Indian Stock Market Intelligence Platform",
        description="AI-powered research assistant for NSE/BSE listed equities, live data, forecasts and signals",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_, exc: Exception):
        logger.exception("unhandled error")
        return JSONResponse({"error": str(exc) or type(exc).__name__}, status_code=500)

    from .routes import (alerts_routes, analysis_routes, dashboard_routes,
                         news_routes, paper_routes, portfolio_routes, predictions_routes,
                         reports_routes, signal_routes, stock_routes, websocket_routes)

    app.include_router(stock_routes.router, prefix="/api")  # includes indices endpoints
    app.include_router(analysis_routes.router, prefix="/api")
    app.include_router(predictions_routes.router, prefix="/api")
    app.include_router(news_routes.router, prefix="/api")
    app.include_router(signal_routes.router, prefix="/api")
    app.include_router(portfolio_routes.router, prefix="/api")
    app.include_router(paper_routes.router, prefix="/api")
    app.include_router(alerts_routes.router, prefix="/api")
    app.include_router(reports_routes.router, prefix="/api")
    app.include_router(dashboard_routes.router, prefix="/api")
    app.include_router(websocket_routes.router, prefix="/api")

    @app.get("/api/health", tags=["health"])
    def health():
        from .models import MarketData

        db = database.SessionLocal()
        try:
            sources = sorted({
                r.data_source
                for r in db.query(MarketData).all()
                if r.data_source and r.data_source not in ("demo",)
            })
            has_official = bool(sources)
        finally:
            db.close()
        return {
            "status": "ok",
            "service": "indian-stock-market-intelligence",
            "data_sources": sources or __import__("app.config", fromlist=["list_sources"]).list_sources(),
            "demo_mode": not has_official,
            "official_data": has_official,
        }

    return app


app = create_app()
