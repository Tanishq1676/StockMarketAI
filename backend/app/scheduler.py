"""Background scheduler (Phase 10).

Uses APScheduler when available, with a simple asyncio fallback that runs
every minute. Jobs:
- refresh market data every 60 seconds (per spec);
- validate predictions after they mature;
- generate hourly market reports during market hours (9:15-15:30 IST);
- generate the closing daily report when the market closes.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

try:
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    HAS_APSCHEDULER = True
except ImportError:  # pragma: no cover
    HAS_APSCHEDULER = False

from .config import MARKET_CLOSE_MINUTES
from .database import SessionLocal
from .models import MarketData
from .reports.helpers import build_market_context
from .predictions.engine import prediction_service
from .reports.service import market_report_service
from .signals.engine import signal_engine

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 60


def _ist_minute_of_day(offset_minutes: int = 0) -> int:
    now = datetime.utcnow()
    ist_hour = (now.hour + 5) % 24
    minute_of_day = (now.hour * 60 + now.minute + offset_minutes + 300) % 1440
    return minute_of_day


def refresh_market_data(limit: int = 500):
    """Refresh market data from official sources only.

    * During market hours the NSE live index snapshot is applied.
    * Outside market hours nothing is overwritten, so the last verified close
      keeps its ``trade_date`` and is never presented as a live price.
    * If the database has no official rows yet, bootstrap the latest session.
    """
    from .data import ingest
    from .models import MarketData

    try:
        result = ingest.refresh_live_indices()
        logger.debug("live index refresh: %s", result)
    except Exception as exc:  # noqa: BLE001
        logger.debug("live index refresh failed: %s", exc)

    db = SessionLocal()
    try:
        has_official = (
            db.query(MarketData)
            .filter(MarketData.data_source.in_(("nse", "bse", "nse-index", "bse-index", "nse-live")))
            .first()
            is not None
        )
    finally:
        db.close()
    if not has_official:
        try:
            logger.info("no official market data stored; bootstrapping latest session")
            ingest.ingest_latest()
        except Exception as exc:  # noqa: BLE001
            logger.warning("bootstrap ingest failed: %s", exc)
        return

    db = SessionLocal()
    try:
        _generate_signals_for_top_movers(db)
    finally:
        db.close()


def ingest_daily_close() -> None:
    """Fetch the latest completed session after the market closes."""
    from .data import ingest

    try:
        result = ingest.ingest_latest()
        logger.info("daily EOD ingest: %s", {k: v for k, v in result.items() if k != "failed_days"})
    except Exception as exc:  # noqa: BLE001
        logger.warning("daily EOD ingest failed: %s", exc)


def _generate_signals_for_top_movers(db) -> None:
    from .models import StockMeta

    active = {
        s.symbol
        for s in db.query(StockMeta).filter(StockMeta.status == "active").all()
    }
    rows = [
        r
        for r in (
            db.query(MarketData)
            .filter(MarketData.data_source.in_(("nse", "bse", "nse-index", "bse-index", "nse-live")))
            .order_by(MarketData.change_pct.desc())
            .limit(60)
            .all()
        )
        if r.symbol in active
    ][:8]
    from .analysis.time_series import time_series_report

    for r in rows:
        try:
            tech = time_series_report(r.symbol)
            if tech.get("data_source") in ("demo", "unavailable"):
                continue
            # persist=False keeps the scheduler from writing a new signal row
            # every minute; the daily ingest refreshes stored signals instead.
            signal_engine.signal_for_symbol(r.symbol, tech, predictions=[], persist=False, store=False)
        except Exception as exc:
            logger.debug("signal generation failed for %s: %s", r.symbol, exc)


def _market_closed_now() -> bool:
    minute_of_day = _ist_minute_of_day()
    return not (9 * 60 + 15 <= minute_of_day <= 15 * 60 + 30)


def validate_pending_predictions() -> None:
    try:
        prediction_service.validate_pending()
    except Exception as exc:
        logger.warning("prediction validation failed: %s", exc)


def generate_hourly_report_if_open() -> None:
    minute_of_day = _ist_minute_of_day()
    if 9 * 60 + 15 <= minute_of_day <= MARKET_CLOSE_MINUTES:
        try:
            market_report_service.generate_report("hourly")
        except Exception as exc:
            logger.warning("hourly report failed: %s", exc)


def generate_daily_report() -> None:
    try:
        market_report_service.generate_report("daily")
    except Exception as exc:
        logger.warning("daily report failed: %s", exc)


class MarketScheduler:
    def __init__(self):
        self.scheduler = None
        self.loop = None

    def start(self) -> None:
        if HAS_APSCHEDULER:
            self.scheduler = BackgroundScheduler()
            self.scheduler.add_job(refresh_market_data, "interval", seconds=REFRESH_INTERVAL_SECONDS, id="refresh_market_data")
            self.scheduler.add_job(validate_pending_predictions, "interval", minutes=30, id="validate_predictions")
            self.scheduler.add_job(generate_hourly_report_if_open, "interval", minutes=30, id="hourly_report")
            # Daily official EOD ingest at ~16:15 IST (after the 15:30 close).
            self.scheduler.add_job(
                ingest_daily_close, "cron", hour=16, minute=15,
                timezone="Asia/Kolkata", id="ingest_daily_close",
            )
            # Daily closing report at ~15:35 IST
            self.scheduler.add_job(generate_daily_report, "cron", minute=5, hour=16, timezone="Asia/Kolkata", id="daily_report")
            self.scheduler.start()
            logger.info("APScheduler started")
        else:
            logger.warning("APScheduler not available; using asyncio loop for refresh jobs")
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.create_task(self._async_loop())

    async def _async_loop(self):
        while True:
            try:
                await asyncio.to_thread(refresh_market_data)
            except Exception as exc:
                logger.warning("async refresh failed: %s", exc)
            await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

    def stop(self):
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
