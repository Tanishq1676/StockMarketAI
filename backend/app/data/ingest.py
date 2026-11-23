"""Official NSE/BSE ingestion into the platform database.

Design rules
------------
* Only official exchange data is written with an official ``source`` label
  (``nse``, ``bse``, ``nse-index``, ``bse-index``, ``nse-live``).
* Synthetic ``demo`` rows are removed for the tracked universe; they are never
  mixed with official rows.
* Ingestion is idempotent: a date range is replaced, not appended, so repeated
  runs cannot create duplicates.
* Every run is recorded in ``ingest_runs`` with counts and the latest session
  date, so the UI/API can state exactly what is loaded and when.
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import distinct, func

from ..database import SessionLocal
from ..models import (HistoricalPrice, IndexHistory, IndexMeta, IngestRun,
                      MarketData, StockMeta)
from . import catalog, official

logger = logging.getLogger(__name__)

# Exact exchange names -> platform index symbols.
NSE_INDEX_NAMES: Dict[str, str] = {
    "NIFTY50": "Nifty 50",
    "NIFTYNEXT50": "Nifty Next 50",
    "NIFTY100": "Nifty 100",
    "NIFTY200": "Nifty 200",
    "NIFTY500": "Nifty 500",
    "BANKNIFTY": "Nifty Bank",
    "FINNIFTY": "Nifty Financial Services",
    "NIFTYMIDCAP150": "Nifty Midcap 150",
    "NIFTYSMALLCAP250": "Nifty Smallcap 250",
    "NIFTYAUTO": "Nifty Auto",
    "NIFTYIT": "Nifty IT",
    "NIFTYPHARMA": "Nifty Pharma",
    "NIFTYFMCG": "Nifty FMCG",
    "NIFTYMETAL": "Nifty Metal",
    "NIFTYENERGY": "Nifty Energy",
    "NIFTYREALTY": "Nifty Realty",
    "NIFTYPSUBANK": "Nifty PSU Bank",
    "NIFTYINFRA": "Nifty Infrastructure",
    "NIFTYMNC": "Nifty MNC",
    "NIFTYCONSUMERDURABLES": "Nifty Consumer Durables",
    "NIFTYOILGAS": "Nifty Oil & Gas",
    "NIFTYDEFENCE": "Nifty India Defence",
    "NIFTYMEDIA": "Nifty Media",
    "NIFTYHEALTHCARE": "Nifty Healthcare Index",
    "NIFTYCAPITALGOODS": "Nifty Capital Goods",
    "NIFTYCONSUMER": "Nifty India Consumption",
    "NIFTYALPHA50": "Nifty Alpha 50",
    "NIFTYMOMENTUM50": "Nifty500 Momentum 50",
    "NIFTYDIVIDEND": "Nifty Dividend Opportunities 50",
    "NIFTYGROWTH": "Nifty Growth Sectors 15",
}

BSE_INDEX_NAMES: Dict[str, str] = {
    "SENSEX": "BSE SENSEX",
    "BANKEX": "BSE BANKEX",
    "BSE100": "BSE 100",
    "BSE200": "BSE 200",
    "BSE500": "BSE 500",
}

OFFICIAL_SOURCES = {"nse", "bse", "nse-index", "bse-index", "nse-live"}
LEGACY_SYNTHETIC_SOURCES = {"demo", "provider"}

NSE_STOCK_URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{stamp}.csv"
NSE_INDEX_URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{stamp}.csv"
BSE_INDEX_URL = "https://api.bseindia.com/BseIndiaAPI/api/IndexArchDailyPAR/w"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ist_now() -> datetime:
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


def _market_open_now() -> bool:
    now = _ist_now()
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 15 <= minutes <= 15 * 60 + 30


def _pct(close: Optional[float], prev: Optional[float]) -> float:
    if close is None or prev is None or prev <= 0:
        return 0.0
    return round((close - prev) / prev * 100.0, 4)


def _start_run(job: str, source: str = "nse") -> Tuple[int, datetime]:
    db = SessionLocal()
    try:
        run = IngestRun(job=job, source=source, started_at=datetime.utcnow(), status="running")
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id, run.started_at
    finally:
        db.close()


def _finish_run(
    run_id: int,
    *,
    status: str,
    fetched: int = 0,
    inserted: int = 0,
    updated: int = 0,
    rejected: int = 0,
    latest_trade_date: Optional[str] = None,
    error: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    db = SessionLocal()
    try:
        run = db.get(IngestRun, run_id)
        if not run:
            return
        run.status = status
        run.finished_at = datetime.utcnow()
        run.rows_fetched = fetched
        run.rows_inserted = inserted
        run.rows_updated = updated
        run.rows_rejected = rejected
        run.latest_trade_date = latest_trade_date
        run.error = error
        run.details = details or {}
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# master data
# ---------------------------------------------------------------------------

def sync_master() -> dict:
    """Align StockMeta/IndexMeta with the official NSE/BSE masters."""
    run_id, _ = _start_run("sync_master", "nse+bse")
    stats = {"stocks": 0, "deactivated": 0, "indices": 0, "errors": []}
    try:
        try:
            nse_master = {r["symbol"]: r for r in official.nse_equity_master() if r.get("series") == "EQ"}
        except Exception as exc:  # noqa: BLE001
            stats["errors"].append(f"NSE master unavailable: {exc}")
            nse_master = {}
        try:
            bse_rows = official.bse_scrip_master()
        except Exception as exc:  # noqa: BLE001
            stats["errors"].append(f"BSE master unavailable: {exc}")
            bse_rows = []
        bse_by_isin = {r["isin"]: r for r in bse_rows if r.get("isin")}
        bse_by_ticker = {r["ticker"].upper(): r for r in bse_rows if r.get("ticker")}

        db = SessionLocal()
        try:
            catalog_symbols = {s["symbol"] for s in catalog.get_stocks()}
            existing = {m.symbol: m for m in db.query(StockMeta).all()}
            for s in catalog.get_stocks():
                symbol = s["symbol"]
                nse_row = nse_master.get(symbol, {})
                isin = nse_row.get("isin") or s.get("isin") or ""
                bse_row = bse_by_isin.get(isin) or bse_by_ticker.get(symbol.upper()) or {}
                meta = existing.get(symbol)
                if meta is None:
                    meta = StockMeta(symbol=symbol, exchange="NSE")
                    db.add(meta)
                    existing[symbol] = meta
                meta.symbol = symbol
                meta.exchange = s.get("exchange", "NSE")
                meta.name = nse_row.get("name") or s.get("name") or symbol
                meta.sector = s.get("sector", "")
                meta.market_cap = s.get("cap", "")
                meta.nse_indices = s.get("indices", [])
                meta.isin = isin or None
                meta.bse_symbol = bse_row.get("ticker", "") or s.get("bse_symbol", "")
                meta.bse_code = bse_row.get("scrip_code") or None
                meta.data_source = "nse"
                meta.status = "active"
                stats["stocks"] += 1
            for symbol, meta in existing.items():
                if symbol not in catalog_symbols and meta.status == "active":
                    meta.status = "inactive"
                    meta.data_source = "unavailable"
                    stats["deactivated"] += 1

            existing_idx = {m.symbol: m for m in db.query(IndexMeta).all()}
            for idx in catalog.get_all_indices():
                meta = existing_idx.get(idx["symbol"])
                if meta is None:
                    meta = IndexMeta(symbol=idx["symbol"], name=idx["name"], type=idx.get("type", "market_index"), exchange=idx.get("exchange", "NSE"))
                    db.add(meta)
                meta.name = idx["name"]
                meta.type = idx.get("type", "market_index")
                meta.exchange = idx.get("exchange", "NSE")
                meta.data_source = "nse" if meta.exchange == "NSE" else "bse"
                stats["indices"] += 1
            db.commit()
        finally:
            db.close()
        _finish_run(run_id, status="completed", fetched=stats["stocks"], inserted=stats["stocks"], details=stats)
    except Exception as exc:  # noqa: BLE001
        logger.exception("master sync failed")
        _finish_run(run_id, status="failed", error=str(exc))
        raise
    return stats


# ---------------------------------------------------------------------------
# EOD ingestion
# ---------------------------------------------------------------------------

def _fetch_stock_rows(d: date, full: bool) -> List[Dict]:
    """Fetch a session's equity bhavcopy, trying every official archive format."""
    if full:
        try:
            rows = official.nse_bhavcopy_full(d)
            if rows:
                return rows
        except official.SourceUnavailable:
            pass
    return official.nse_bhavcopy(d)


def _build_stock_records(rows: Iterable[Dict], universe: Set[str], fetched_at: datetime) -> List[Dict]:
    out = []
    for r in rows:
        if r["symbol"] not in universe:
            continue
        close = r.get("close")
        prev = r.get("prev_close")
        if close is None or close <= 0:
            continue
        out.append(
            {
                "symbol": r["symbol"],
                "date": r["date"],
                "open": r.get("open") or close,
                "high": r.get("high") or close,
                "low": r.get("low") or close,
                "close": close,
                "volume": int(r.get("volume") or 0),
                "pct_change": _pct(close, prev),
                "prev_close": prev,
                "source": "nse",
                "exchange": "NSE",
                "fetched_at": fetched_at,
            }
        )
    return out


def _index_key(name: str) -> str:
    """Normalise an exchange index name for matching.

    BSE publishes the same index as both ``SENSEX`` (range endpoint) and
    ``BSE SENSEX`` (all-indices endpoint); NSE uses ``Nifty 50`` style names.
    """
    text = (name or "").upper().replace("&", " ").replace("S&P", " ")
    text = text.replace("BSE", " ")
    return " ".join(text.split())


def _build_index_records(rows: Iterable[Dict], mapping: Dict[str, str], exchange: str, source: str, fetched_at: datetime) -> List[Dict]:
    reverse = {_index_key(v): k for k, v in mapping.items()}
    out = []
    for r in rows:
        symbol = reverse.get(_index_key(r.get("name", "")))
        if not symbol:
            continue
        close = r.get("close")
        if close is None or close <= 0:
            continue
        prev = r.get("prev_close")
        pct = r.get("change_pct")
        if prev is None and r.get("change_points") is not None:
            prev = close - float(r["change_points"])
        if pct is None:
            pct = _pct(close, prev)
        out.append(
            {
                "symbol": symbol,
                "date": r["date"],
                "open": r.get("open") or close,
                "high": r.get("high") or close,
                "low": r.get("low") or close,
                "close": close,
                "volume": int(r.get("volume") or 0),
                "pct_change": pct,
                "prev_close": prev,
                "source": source,
                "exchange": exchange,
                "fetched_at": fetched_at,
            }
        )
    return out


def _replace_historical(db, source: str, dates: List[str], records: List[Dict]) -> int:
    if not dates:
        return 0
    db.query(HistoricalPrice).filter(
        HistoricalPrice.source == source, HistoricalPrice.date.in_(dates)
    ).delete(synchronize_session=False)
    for chunk_start in range(0, len(records), 5000):
        db.bulk_insert_mappings(HistoricalPrice, records[chunk_start:chunk_start + 5000])
    return len(records)


def _replace_index_history(db, source: str, dates: List[str], records: List[Dict]) -> int:
    if not dates:
        return 0
    db.query(IndexHistory).filter(
        IndexHistory.source == source, IndexHistory.date.in_(dates)
    ).delete(synchronize_session=False)
    rows = [
        {**{k: v for k, v in r.items() if k != "exchange"}, "source": source}
        for r in records
    ]
    for chunk_start in range(0, len(rows), 5000):
        db.bulk_insert_mappings(IndexHistory, rows[chunk_start:chunk_start + 5000])
    return len(rows)


def _latest_by_symbol(records: Iterable[Dict]) -> Dict[str, Dict]:
    latest: Dict[str, Dict] = {}
    for r in records:
        current = latest.get(r["symbol"])
        if current is None or r["date"] > current["date"]:
            latest[r["symbol"]] = r
    return latest


def _upsert_market_rows(db, latest: Dict[str, Dict], source: str, exchange: str, fetched_at: datetime, source_url: str) -> int:
    if not latest:
        return 0
    symbols = list(latest.keys())
    db.query(MarketData).filter(MarketData.symbol.in_(symbols)).delete(synchronize_session=False)
    for symbol, r in latest.items():
        close = float(r["close"])
        prev = r.get("prev_close")
        pct = r.get("pct_change")
        if pct is None:
            pct = _pct(close, prev)
        db.add(
            MarketData(
                symbol=symbol,
                price_open=float(r.get("open") or close),
                price_high=float(r.get("high") or close),
                price_low=float(r.get("low") or close),
                price_close=close,
                volume=int(r.get("volume") or 0),
                change_pct=float(pct or 0.0),
                prev_close=float(prev) if prev is not None else None,
                last_updated=fetched_at,
                trade_date=r["date"],
                fetched_at=fetched_at,
                source_url=source_url,
                data_source=source,
                is_live=False,
                delay_minutes=0,
            )
        )
    return len(latest)


def ingest_eod(start: date, end: date, *, include_bse_history: bool = True, full_latest: bool = True) -> dict:
    """Backfill/refresh official EOD data for the catalog universe."""
    run_id, started = _start_run("ingest_eod", "nse+bse")
    stats = {
        "days": 0,
        "stock_rows": 0,
        "index_rows": 0,
        "bse_rows": 0,
        "failed_days": [],
        "skipped_days": [],
        "latest_trade_date": None,
    }
    fetched_at = datetime.utcnow()
    days = official.trading_days(start, end)
    if not days:
        _finish_run(run_id, status="completed", details=stats)
        return stats
    universe = {s["symbol"] for s in catalog.get_stocks()}
    stock_records: List[Dict] = []
    index_records: List[Dict] = []
    nse_dates: List[str] = []
    index_dates: List[str] = []
    latest_day = days[-1]

    db = SessionLocal()
    try:
        # Remove synthetic history for the tracked universe once, before the
        # official rows are written.  Other sources/dates are left untouched.
        db.query(HistoricalPrice).filter(
            HistoricalPrice.source.in_(list(LEGACY_SYNTHETIC_SOURCES))
        ).delete(synchronize_session=False)
        db.commit()

        for i, d in enumerate(days, start=1):
            stock_ok = False
            index_ok = False
            stock_error = None
            index_error = None
            try:
                rows = _fetch_stock_rows(d, full=(full_latest and d == latest_day))
                recs = _build_stock_records(rows, universe, fetched_at)
                stock_ok = bool(recs)
                if recs:
                    stock_records.extend(recs)
                    nse_dates.append(d.isoformat())
                stats["stock_rows"] += len(recs)
            except Exception as exc:  # noqa: BLE001
                stock_error = str(exc)[:200]
            try:
                idx_rows = official.nse_index_close(d)
                recs = _build_index_records(idx_rows, NSE_INDEX_NAMES, "NSE", "nse-index", fetched_at)
                index_ok = bool(recs)
                if recs:
                    index_records.extend(recs)
                    index_dates.append(d.isoformat())
                stats["index_rows"] += len(recs)
            except Exception as exc:  # noqa: BLE001
                index_error = str(exc)[:200]
            if not stock_ok and not index_ok:
                # Neither dataset exists for the day: an exchange holiday the
                # calendar did not list.  Not a failure.
                stats["skipped_days"].append(d.isoformat())
            else:
                if not stock_ok:
                    stats["failed_days"].append({"date": d.isoformat(), "dataset": "equities", "error": stock_error})
                if not index_ok:
                    stats["failed_days"].append({"date": d.isoformat(), "dataset": "indices", "error": index_error})
            if i % 25 == 0 or i == len(days):
                logger.info("EOD ingest %d/%d days (%s)", i, len(days), d.isoformat())
                db.commit()

        inserted = _replace_historical(db, "nse", nse_dates, stock_records)
        inserted += _replace_historical(db, "nse-index", index_dates, index_records)
        inserted += _replace_index_history(db, "nse", index_dates, index_records)
        db.commit()

        # ---- BSE SENSEX history (one request for the whole range) ----
        if include_bse_history:
            try:
                sensex = official.bse_index_history("SENSEX", start, end)
                recs = _build_index_records(sensex, BSE_INDEX_NAMES, "BSE", "bse-index", fetched_at)
                if recs:
                    bse_dates = sorted({r["date"] for r in recs})
                    _replace_historical(db, "bse-index", bse_dates, recs)
                    _replace_index_history(db, "bse", bse_dates, recs)
                    stats["bse_rows"] += len(recs)
                    db.commit()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                stats["failed_days"].append({"date": "SENSEX", "dataset": "bse-index", "error": str(exc)[:200]})

        # ---- BSE index snapshot for the latest session (BANKEX/100/200/500) ----
        try:
            bse_today = official.bse_all_indices(latest_day)
            recs = _build_index_records(bse_today, BSE_INDEX_NAMES, "BSE", "bse-index", fetched_at)
            recs = [r for r in recs if r["symbol"] != "SENSEX"]
            if recs:
                bse_dates = sorted({r["date"] for r in recs})
                symbols = sorted({r["symbol"] for r in recs})
                db.query(HistoricalPrice).filter(
                    HistoricalPrice.source == "bse-index",
                    HistoricalPrice.date.in_(bse_dates),
                    HistoricalPrice.symbol.in_(symbols),
                ).delete(synchronize_session=False)
                db.query(IndexHistory).filter(
                    IndexHistory.date.in_(bse_dates),
                    IndexHistory.symbol.in_(symbols),
                ).delete(synchronize_session=False)
                db.bulk_insert_mappings(HistoricalPrice, recs)
                db.bulk_insert_mappings(
                    IndexHistory,
                    [{**{k: v for k, v in r.items() if k != "exchange"}, "source": "bse"} for r in recs],
                )
                stats["bse_rows"] += len(recs)
                db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            stats["failed_days"].append({"date": latest_day.isoformat(), "dataset": "bse-indices", "error": str(exc)[:200]})

        # ---- latest quote rows ----
        stock_latest = _latest_by_symbol(stock_records)
        index_latest = _latest_by_symbol(index_records)
        bse_latest: Dict[str, Dict] = {}
        try:
            for r in _build_index_records(official.bse_all_indices(latest_day), BSE_INDEX_NAMES, "BSE", "bse-index", fetched_at):
                bse_latest[r["symbol"]] = r
        except Exception:
            pass
        if include_bse_history:
            try:
                sensex = official.bse_index_history("SENSEX", max(start, end - timedelta(days=10)), end)
                for r in _build_index_records(sensex, BSE_INDEX_NAMES, "BSE", "bse-index", fetched_at):
                    bse_latest[r["symbol"]] = r
            except Exception:
                pass
        _upsert_market_rows(db, stock_latest, "nse", "NSE", fetched_at, NSE_STOCK_URL.format(stamp=latest_day.strftime("%d%m%Y")))
        _upsert_market_rows(db, index_latest, "nse-index", "NSE", fetched_at, NSE_INDEX_URL.format(stamp=latest_day.strftime("%d%m%Y")))
        _upsert_market_rows(db, bse_latest, "bse-index", "BSE", fetched_at, BSE_INDEX_URL)
        db.commit()

        stats["days"] = len(days)
        latest_stock_date = max((r["date"] for r in stock_latest.values()), default=None)
        stats["latest_trade_date"] = latest_stock_date
        _finish_run(
            run_id,
            status="completed" if not stats["failed_days"] else "completed_with_warnings",
            fetched=stats["stock_rows"] + stats["index_rows"] + stats["bse_rows"],
            inserted=inserted,
            rejected=len(stats["failed_days"]),
            latest_trade_date=stats["latest_trade_date"],
            details={k: v for k, v in stats.items() if k != "failed_days"} | {"failed_days": stats["failed_days"][:20]},
        )
        logger.info("EOD ingest complete: %s", {k: v for k, v in stats.items() if k != "failed_days"})
        return stats
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("EOD ingest failed")
        _finish_run(run_id, status="failed", error=str(exc), details=stats)
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# BSE index ingest
# ---------------------------------------------------------------------------

def ingest_bse_indices(start: date, end: date) -> dict:
    """Ingest official BSE index data.

    SENSEX has a full daily archive for a date range; the other tracked BSE
    indices (BANKEX, BSE 100/200/500) are published one session at a time, so
    only the latest session is ingested for them.
    """
    run_id, _ = _start_run("ingest_bse_indices", "bse")
    stats = {"rows": 0, "latest_trade_date": None, "errors": []}
    fetched_at = datetime.utcnow()
    bse_latest: Dict[str, Dict] = {}
    db = SessionLocal()
    try:
        try:
            sensex = official.bse_index_history("SENSEX", start, end)
            recs = _build_index_records(sensex, BSE_INDEX_NAMES, "BSE", "bse-index", fetched_at)
            if recs:
                dates = sorted({r["date"] for r in recs})
                _replace_historical(db, "bse-index", dates, recs)
                _replace_index_history(db, "bse", dates, recs)
                stats["rows"] += len(recs)
                stats["latest_trade_date"] = dates[-1]
                bse_latest["SENSEX"] = recs[-1]
                db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            stats["errors"].append(f"SENSEX: {exc}")

        latest_day = date.fromisoformat(stats["latest_trade_date"]) if stats["latest_trade_date"] else end
        try:
            all_rows = official.bse_all_indices(latest_day)
            recs = _build_index_records(all_rows, BSE_INDEX_NAMES, "BSE", "bse-index", fetched_at)
            if recs:
                dates = sorted({r["date"] for r in recs})
                symbols = sorted({r["symbol"] for r in recs})
                db.query(HistoricalPrice).filter(
                    HistoricalPrice.source == "bse-index",
                    HistoricalPrice.date.in_(dates),
                    HistoricalPrice.symbol.in_(symbols),
                ).delete(synchronize_session=False)
                db.query(IndexHistory).filter(
                    IndexHistory.date.in_(dates),
                    IndexHistory.symbol.in_(symbols),
                ).delete(synchronize_session=False)
                db.bulk_insert_mappings(HistoricalPrice, recs)
                db.bulk_insert_mappings(
                    IndexHistory,
                    [{**{k: v for k, v in r.items() if k != "exchange"}, "source": "bse"} for r in recs],
                )
                stats["rows"] += len(recs)
                for r in recs:
                    bse_latest[r["symbol"]] = r
                db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            stats["errors"].append(f"all-indices: {exc}")

        if bse_latest:
            _upsert_market_rows(db, bse_latest, "bse-index", "BSE", fetched_at, BSE_INDEX_URL)
            db.commit()

        _finish_run(
            run_id,
            status="completed" if not stats["errors"] else "completed_with_warnings",
            fetched=stats["rows"],
            inserted=stats["rows"],
            latest_trade_date=stats["latest_trade_date"],
            error="; ".join(stats["errors"])[:1000] if stats["errors"] else None,
            details=stats,
        )
        logger.info("BSE index ingest complete: %s", stats)
        return stats
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        _finish_run(run_id, status="failed", error=str(exc))
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# latest session + live index refresh
# ---------------------------------------------------------------------------

def latest_trading_day(lookback_days: int = 12) -> Optional[date]:
    """Most recent session for which NSE publishes a bhavcopy."""
    today = date.today()
    candidates = official.trading_days(today - timedelta(days=lookback_days), today)
    for d in reversed(candidates):
        try:
            rows = official.nse_bhavcopy_udiff(d)
            if rows:
                return d
        except official.SourceUnavailable:
            continue
    return None


def ingest_latest() -> dict:
    """Ingest the most recent available session (and BSE indices for it)."""
    d = latest_trading_day()
    if d is None:
        raise official.SourceUnavailable("no recent NSE session available")
    return ingest_eod(d, d, include_bse_history=False, full_latest=True)


def refresh_live_indices() -> dict:
    """Refresh index quotes from NSE's official live snapshot.

    Only runs while the market is open; outside market hours the last official
    close remains untouched, so an EOD close is never presented as live.
    """
    if not _market_open_now():
        return {"updated": 0, "reason": "market_closed"}
    try:
        rows = official.nse_all_indices()
    except Exception as exc:  # noqa: BLE001
        logger.debug("live index refresh unavailable: %s", exc)
        return {"updated": 0, "reason": str(exc)[:120]}
    reverse = {v: k for k, v in NSE_INDEX_NAMES.items()}
    now = datetime.utcnow()
    updated = 0
    db = SessionLocal()
    try:
        for r in rows:
            symbol = reverse.get(r.get("name", "").strip())
            if not symbol:
                continue
            row = db.query(MarketData).filter(MarketData.symbol == symbol).first()
            if row is None:
                row = MarketData(symbol=symbol)
                db.add(row)
            close = float(r["close"])
            prev = r.get("prev_close")
            row.price_open = float(r.get("open") or close)
            row.price_high = float(r.get("high") or close)
            row.price_low = float(r.get("low") or close)
            row.price_close = close
            row.volume = int(r.get("volume") or 0)
            row.change_pct = float(r.get("change_pct") or _pct(close, prev))
            row.prev_close = float(prev) if prev is not None else None
            row.last_updated = now
            row.trade_date = _ist_now().date().isoformat()
            row.fetched_at = now
            row.source_url = "https://www.nseindia.com/api/allIndices"
            row.data_source = "nse-live"
            row.is_live = True
            row.delay_minutes = 0
            updated += 1
        db.commit()
    finally:
        db.close()
    return {"updated": updated, "reason": "ok"}


def coverage_report() -> dict:
    """Summary of what official data is currently stored."""
    db = SessionLocal()
    try:
        sources = [
            {"source": r[0], "rows": r[1]}
            for r in db.query(HistoricalPrice.source, func.count(HistoricalPrice.id))
            .group_by(HistoricalPrice.source)
            .all()
        ]
        stock_range = db.query(
            func.min(HistoricalPrice.date),
            func.max(HistoricalPrice.date),
            func.count(HistoricalPrice.id),
            func.count(distinct(HistoricalPrice.symbol)),
        ).filter(HistoricalPrice.source.in_(["nse", "bse"])).one()
        index_range = db.query(
            func.min(IndexHistory.date),
            func.max(IndexHistory.date),
            func.count(IndexHistory.id),
        ).one()
        latest = (
            db.query(MarketData)
            .filter(MarketData.data_source.in_(list(OFFICIAL_SOURCES)))
            .order_by(MarketData.trade_date.desc(), MarketData.fetched_at.desc())
            .first()
        )
        return {
            "sources": sources,
            "stocks": {
                "rows": stock_range[2],
                "symbols": stock_range[3],
                "first_date": stock_range[0],
                "last_date": stock_range[1],
            },
            "indices": {"rows": index_range[2], "first_date": index_range[0], "last_date": index_range[1]},
            "latest_trade_date": latest.trade_date if latest else None,
            "latest_fetched_at": latest.fetched_at.isoformat() if latest and latest.fetched_at else None,
        }
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest official NSE/BSE market data")
    parser.add_argument("--start", help="start date YYYY-MM-DD")
    parser.add_argument("--end", help="end date YYYY-MM-DD")
    parser.add_argument("--latest", action="store_true", help="ingest only the latest session")
    parser.add_argument("--bse-only", action="store_true", help="ingest only BSE index data")
    parser.add_argument("--no-bse-history", action="store_true")
    parser.add_argument("--skip-master", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not args.skip_master:
        print("master:", sync_master())
    end = date.fromisoformat(args.end) if args.end else date.today()
    start = date.fromisoformat(args.start) if args.start else end - timedelta(days=365)
    if args.bse_only:
        print("bse:", ingest_bse_indices(start, end))
    elif args.latest:
        print("latest:", ingest_latest())
    else:
        print("eod:", ingest_eod(start, end, include_bse_history=not args.no_bse_history))
    print("coverage:", coverage_report())


if __name__ == "__main__":
    main()
