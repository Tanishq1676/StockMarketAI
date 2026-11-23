"""Provider interface + demo + real providers.

Provider methods are best-effort: a real provider that cannot answer (no
key, network error, API outages, unsupported symbol) raises
`ProviderUnavailable` and callers fall back to demo mode. Every returned
payload marks its provenance via `source`/`is_live`/`delay_minutes`.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from ..config import ALPHA_VANTAGE_API_KEY, ALPHA_VANTAGE_BASE_URL, TWELVE_DATA_API_KEY, TWELVE_DATA_BASE_URL
from . import demo_data

logger = logging.getLogger(__name__)


class ProviderUnavailable(Exception):
    """Raised when the configured provider cannot service a request."""


@dataclass
class Quote:
    symbol: str
    name: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    change_pct: float  # percent, e.g. 1.12 means +1.12%
    last_updated: str
    source: str
    is_live: bool = False
    delay_minutes: int = 0
    prev_close: Optional[float] = None
    trade_date: Optional[str] = None
    fetched_at: Optional[str] = None
    source_url: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class SearchResult:
    symbol: str
    name: str
    exchange: str
    sector: str = ""
    cap: str = ""
    indices: List[str] = None


@dataclass
class HistoryRow:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str = "demo"


class Provider(ABC):
    name = "base"

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote: ...

    @abstractmethod
    def get_history(self, symbol: str, start_date: str, end_date: str) -> List[HistoryRow]: ...

    @abstractmethod
    def search_stocks(self, query: str, limit: int = 20) -> List[SearchResult]: ...

    @abstractmethod
    def get_name(self, symbol: str) -> str: ...


class DemoProvider(Provider):
    """Fully functional, clearly labelled demo data source."""

    name = "demo"

    def get_quote(self, symbol: str) -> Quote:
        from .catalog import find_stock

        meta = find_stock(symbol)
        hist = demo_data.generate_history(symbol, days=400)
        quote_data = demo_data.generate_realtime_quote(symbol, hist)
        return Quote(
            symbol=symbol,
            name=(meta["name"] if meta else symbol),
            open=quote_data["open"],
            high=quote_data["high"],
            low=quote_data["low"],
            close=quote_data["close"],
            volume=quote_data["volume"],
            # Demo values are fractions internally; expose percent so every
            # quote in the platform uses one unit.
            change_pct=round(float(quote_data["change_pct"]) * 100.0, 4),
            last_updated=quote_data["last_updated"],
            source="demo",
            is_live=False,
            delay_minutes=0,
            trade_date=quote_data["last_updated"][:10],
            raw={"note": "synthetic demo data, not real market data"},
        )

    def get_history(self, symbol: str, start_date: str, end_date: str) -> List[HistoryRow]:
        from datetime import date

        rows = demo_data.generate_history(symbol, days=10_000)
        out = [
            HistoryRow(
                date=h.date,
                open=h.open,
                high=h.high,
                low=h.low,
                close=h.close,
                volume=h.volume,
            )
            for h in rows
            if start_date <= h.date <= end_date
        ]
        # generate_history returns the most recent first.
        return list(reversed(out))

    def search_stocks(self, query: str, limit: int = 20) -> List[SearchResult]:
        from .catalog import search_stocks as catalog_search

        return catalog_search(query, limit)

    def get_name(self, symbol: str) -> str:
        from .catalog import find_stock

        meta = find_stock(symbol)
        return meta["name"] if meta else symbol


class AlphaVantageProvider(Provider):
    """Best-effort real provider. Without a valid key every call raises."""

    name = "alpha-vantage"

    def __init__(self):
        self.key = ALPHA_VANTAGE_API_KEY
        if not self.key:
            raise ProviderUnavailable("ALPHA_VANTAGE_API_KEY is not configured")

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(f"{ALPHA_VANTAGE_BASE_URL}/query", params={**params, "apikey": self.key})
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # network/parse/HTTP errors
            raise ProviderUnavailable(f"alpha vantage call failed: {exc}") from exc
        if "Error Message" in data or "Information" in data and "Free tier" in str(data.get("Information", "")):
            raise ProviderUnavailable(f"alpha vantage returned error: {data.get('Error Message')}")
        return data

    def get_quote(self, symbol: str) -> Quote:
        data = self._get("quote", {"function": "GLOBAL_QUOTE", "symbol": symbol})
        if "Global Quote" not in data:
            raise ProviderUnavailable("no quote returned for symbol")
        q = data["Global Quote"]
        return Quote(
            symbol=symbol,
            name=symbol,
            open=float(q["02. open"]),
            high=float(q["03. high"]),
            low=float(q["04. low"]),
            close=float(q["05. price"]),
            volume=int(float(q["06. volume"])),
            change_pct=float(q["09. change"]) / max(float(q["08. previous close"]), 1) * 100.0,
            last_updated=q["07. latest trading day"] + " 15:30:00",
            source=self.name,
            is_live=False,
            delay_minutes=30,
        )

    def get_history(self, symbol: str, start_date: str, end_date: str) -> List[HistoryRow]:
        data = self._get("ts", {"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": symbol, "outputsize": "full", "fulldata": "False"})
        rows = [
            HistoryRow(
                date=d,
                open=float(v["1. open"]),
                high=float(v["2. high"]),
                low=float(v["3. low"]),
                close=float(v["4. close"]),
                volume=int(float(v["7. volume"])),
            )
            for d, v in sorted(data.get("Time Series (Daily)", {}).items())
            if start_date <= d <= end_date
        ]
        return rows

    def search_stocks(self, query: str, limit: int = 20) -> List[SearchResult]:
        # Alpha Vantage has no Indian-name search endpoint; best-effort via
        # the stock search for NSE (symbol endpoint not reliable).
        raise ProviderUnavailable("search not supported by alpha vantage; use demo catalog")

    def get_name(self, symbol: str) -> str:
        from .catalog import find_stock

        meta = find_stock(symbol)
        return meta["name"] if meta else symbol


class TwelveDataProvider(Provider):
    """Best-effort real provider using Twelve Data API."""

    name = "twelve-data"

    def __init__(self):
        if not TWELVE_DATA_API_KEY:
            raise ProviderUnavailable("TWELVE_DATA_API_KEY is not configured")
        self.headers = {"apikey": TWELVE_DATA_API_KEY}

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(f"{TWELVE_DATA_BASE_URL}/{path}", params=params, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise ProviderUnavailable(f"twelve data call failed: {exc}") from exc
        if data.get("status") not in (None, 200) or "message" in data:
            raise ProviderUnavailable(f"twelve data returned error: {data.get('message')}")
        return data

    def _eod_rows(self, symbol: str, start_date: str, end_date: str) -> List[HistoryRow]:
        data = self._get(
            "api/price/eod",
            {"symbol": f"{symbol}:NSE", "format": "json", "outputsize": "30"},
        )
        rows = [
            HistoryRow(
                date=r["date"][:10],
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                volume=int(r.get("volume", 0)),
            )
            for r in data.get("values", [])
            if start_date <= r["date"][:10] <= end_date
        ]
        return rows

    def get_quote(self, symbol: str) -> Quote:
        for sym in (f"{symbol}:NSE", f"{symbol}:BSE", symbol):
            data = self._get("api/price/quote", {"symbol": sym, "format": "json"})
            try:
                quote = data["symbol"]
                cp = data["quote"]
                price = float(cp["price"])
                prev_close = float(cp["previous_close"])
                return Quote(
                    symbol=sym,
                    name=data.get("name", symbol),
                    open=float(cp["open"]),
                    high=float(cp["day_high"]),
                    low=float(cp["day_low"]),
                    close=price,
                    volume=int(cp.get("volume", 0)),
                    change_pct=(price - prev_close) / prev_close * 100.0 if prev_close else 0.0,
                    last_updated=cp["timestamp"],
                    source=self.name,
                    is_live=True,
                    delay_minutes=0,
                )
            except KeyError:
                continue
        raise ProviderUnavailable("no quote returned for symbol")

    def get_history(self, symbol: str, start_date: str, end_date: str) -> List[HistoryRow]:
        try:
            rows = self._eod_rows(symbol, start_date, end_date)
        except ProviderUnavailable:
            # Fall back to daily EOD? twelve data: use "api/price/history" (greater)
            raise
        return sorted(rows, key=lambda r: r.date)

    def search_stocks(self, query: str, limit: int = 20) -> List[SearchResult]:
        from .catalog import search_stocks as catalog_search

        return catalog_search(query, limit)

    def get_name(self, symbol: str) -> str:
        from .catalog import find_stock

        meta = find_stock(symbol)
        return meta["name"] if meta else symbol


_PROVIDER_ORDER = ["twelve-data", "alpha-vantage", "demo"]

# Sources written by the official NSE/BSE ingestion layer.  These always win
# over any demo or third-party fallback.
OFFICIAL_SOURCES = ("nse", "bse", "nse-index", "bse-index", "nse-live")


def _quote_from_db(symbol: str) -> Optional[Quote]:
    """Return the stored official quote for a symbol, if one exists."""
    from ..database import SessionLocal
    from ..models import IndexMeta, MarketData, StockMeta

    db = SessionLocal()
    try:
        row = (
            db.query(MarketData)
            .filter(
                MarketData.symbol == symbol,
                MarketData.data_source.in_(OFFICIAL_SOURCES),
            )
            .order_by(MarketData.trade_date.desc(), MarketData.last_updated.desc())
            .first()
        )
        if row is None:
            return None
        name = symbol
        meta = db.query(StockMeta).filter(StockMeta.symbol == symbol).first()
        if meta is not None:
            name = meta.name
        else:
            idx = db.query(IndexMeta).filter(IndexMeta.symbol == symbol).first()
            if idx is not None:
                name = idx.name
        return Quote(
            symbol=symbol,
            name=name,
            open=float(row.price_open),
            high=float(row.price_high),
            low=float(row.price_low),
            close=float(row.price_close),
            volume=int(row.volume or 0),
            change_pct=float(row.change_pct or 0.0),
            last_updated=(row.fetched_at or row.last_updated).isoformat() if (row.fetched_at or row.last_updated) else "",
            source=row.data_source,
            is_live=bool(row.is_live),
            delay_minutes=int(row.delay_minutes or 0),
            prev_close=float(row.prev_close) if row.prev_close is not None else None,
            trade_date=row.trade_date,
            fetched_at=row.fetched_at.isoformat() if row.fetched_at else None,
            source_url=row.source_url,
        )
    finally:
        db.close()


def get_provider(preferred: Optional[str] = None) -> Provider:
    """Resolve the active provider: preferred -> TWELVE_DATA -> ALPHA_VANTAGE -> demo."""
    order = [preferred] + _PROVIDER_ORDER if preferred else _PROVIDER_ORDER
    errors = []
    for name in order:
        if name == "twelve-data":
            try:
                return TwelveDataProvider()
            except ProviderUnavailable as exc:
                errors.append(str(exc))
        elif name == "alpha-vantage":
            try:
                return AlphaVantageProvider()
            except ProviderUnavailable as exc:
                errors.append(str(exc))
        elif name == "demo":
            if errors and preferred != "demo":
                logger.warning("real providers unavailable (%s); falling back to demo mode", "; ".join(errors))
            return DemoProvider()
    return DemoProvider()


def get_quote(symbol: str, preferred: Optional[str] = None) -> Quote:
    """Return an official stored quote, else a configured real provider.

    Synthetic demo quotes are produced only when ``preferred="demo"`` is
    requested explicitly.  They are never a silent fallback, so a fabricated
    price can never be mistaken for a real one.
    """
    if preferred == "demo":
        return DemoProvider().get_quote(symbol)
    stored = _quote_from_db(symbol)
    if stored is not None:
        return stored
    provider = get_provider(preferred)
    if provider.name == "demo":
        raise ProviderUnavailable(f"no official quote stored for {symbol}")
    return provider.get_quote(symbol)


def get_history(symbol: str, start_date: str, end_date: str, preferred: Optional[str] = None) -> List[HistoryRow]:
    provider = get_provider(preferred)
    try:
        return provider.get_history(symbol, start_date, end_date)
    except ProviderUnavailable:
        if provider.name != "demo":
            return DemoProvider().get_history(symbol, start_date, end_date)
        raise
