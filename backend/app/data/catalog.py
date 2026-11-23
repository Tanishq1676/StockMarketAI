"""In-memory catalog of Indian stocks and indices (source of truth)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

MASTER_STOCKS_FILE = Path(__file__).resolve().parent / "master_stocks.json"

# Index catalogue.  `nse_name` / `bse_name` are the exact names published by
# the exchanges and are used by the ingestion layer to map rows to symbols.
DEFAULT_INDICES = [
    {"symbol": "NIFTY50", "name": "NIFTY 50", "type": "market_index", "exchange": "NSE"},
    {"symbol": "NIFTYNEXT50", "name": "NIFTY NEXT 50", "type": "market_index", "exchange": "NSE"},
    {"symbol": "NIFTY100", "name": "NIFTY 100", "type": "market_index", "exchange": "NSE"},
    {"symbol": "NIFTY200", "name": "NIFTY 200", "type": "market_index", "exchange": "NSE"},
    {"symbol": "NIFTY500", "name": "NIFTY 500", "type": "market_index", "exchange": "NSE"},
    {"symbol": "NIFTYMIDCAP150", "name": "NIFTY MIDCAP 150", "type": "market_index", "exchange": "NSE"},
    {"symbol": "NIFTYSMALLCAP250", "name": "NIFTY SMALLCAP 250", "type": "market_index", "exchange": "NSE"},
    {"symbol": "BANKNIFTY", "name": "NIFTY BANK", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "FINNIFTY", "name": "NIFTY FINANCIAL SERVICES", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYAUTO", "name": "NIFTY AUTO", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYIT", "name": "NIFTY IT", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYPHARMA", "name": "NIFTY PHARMA", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYFMCG", "name": "NIFTY FMCG", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYMETAL", "name": "NIFTY METAL", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYENERGY", "name": "NIFTY ENERGY", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYREALTY", "name": "NIFTY REALTY", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYPSUBANK", "name": "NIFTY PSU BANK", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYINFRA", "name": "NIFTY INFRASTRUCTURE", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYMNC", "name": "NIFTY MNC", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYCONSUMERDURABLES", "name": "NIFTY CONSUMER DURABLES", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYOILGAS", "name": "NIFTY OIL & GAS", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYDEFENCE", "name": "NIFTY INDIA DEFENCE", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYMEDIA", "name": "NIFTY MEDIA", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYHEALTHCARE", "name": "NIFTY HEALTHCARE", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYCAPITALGOODS", "name": "NIFTY CAPITAL GOODS", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYCONSUMER", "name": "NIFTY INDIA CONSUMPTION", "type": "sectoral", "exchange": "NSE"},
    {"symbol": "NIFTYALPHA50", "name": "NIFTY ALPHA 50", "type": "strategy", "exchange": "NSE"},
    {"symbol": "NIFTYMOMENTUM50", "name": "NIFTY500 MOMENTUM 50", "type": "strategy", "exchange": "NSE"},
    {"symbol": "NIFTYDIVIDEND", "name": "NIFTY DIVIDEND OPPORTUNITIES 50", "type": "strategy", "exchange": "NSE"},
    {"symbol": "NIFTYGROWTH", "name": "NIFTY GROWTH SECTORS 15", "type": "strategy", "exchange": "NSE"},
    {"symbol": "SENSEX", "name": "S&P BSE SENSEX", "type": "market_index", "exchange": "BSE"},
    {"symbol": "BANKEX", "name": "S&P BSE BANKEX", "type": "sectoral", "exchange": "BSE"},
    {"symbol": "BSE100", "name": "S&P BSE 100", "type": "market_index", "exchange": "BSE"},
    {"symbol": "BSE200", "name": "S&P BSE 200", "type": "market_index", "exchange": "BSE"},
    {"symbol": "BSE500", "name": "S&P BSE 500", "type": "market_index", "exchange": "BSE"},
]


def _load_stocks() -> List[dict]:
    with MASTER_STOCKS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


_STOCKS: Optional[List[dict]] = None


def get_stocks() -> List[dict]:
    global _STOCKS
    if _STOCKS is None:
        _STOCKS = _load_stocks()
    return _STOCKS


def find_stock(symbol: str) -> Optional[dict]:
    needle = symbol.strip().upper()
    for s in get_stocks():
        if s["symbol"].upper() == needle or s.get("bse_symbol", "").upper() == needle:
            return s
    return None


def get_all_indices() -> List[dict]:
    """Every tracked index, de-duplicated by symbol."""
    indices: List[dict] = []
    seen = set()
    for item in DEFAULT_INDICES:
        symbol = item["symbol"]
        if symbol in seen:
            continue
        seen.add(symbol)
        indices.append(dict(item))
    return indices


def search_stocks(query: str, limit: int = 20) -> List[dict]:
    q = query.strip().lower()
    if not q:
        return get_stocks()[:limit]
    exact = []
    fuzzy = []
    for s in get_stocks():
        sym = s["symbol"].lower()
        name = s["name"].lower()
        sector = s.get("sector", "").lower()
        if q in sym or q in name.split()[0].lower() or q in name:
            if q in sym:
                exact.append(s)
            else:
                fuzzy.append(s)
        elif q in sector:
            fuzzy.append(s)
    return (exact + fuzzy)[:limit]
