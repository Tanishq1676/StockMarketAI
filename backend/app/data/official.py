"""Official NSE / BSE market-data fetchers.

This module talks **only** to the exchanges' public archive files and public
JSON endpoints.  It never bypasses authentication or access restrictions: the
BSE endpoints are ordinary public web endpoints that expect browser-equivalent
headers and a primed cookie, which is exactly what a browser sends.

Every parser returns plain dictionaries so the ingestion layer can validate
them before anything reaches the database.  Raw downloads are cached on disk
so a retried backfill does not hammer the exchanges.
"""

from __future__ import annotations

import csv
import http.cookiejar
import io
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..config import BACKEND_DIR

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

NSE_ARCHIVE = "https://nsearchives.nseindia.com"
NSE_WEB = "https://www.nseindia.com"
BSE_API = "https://api.bseindia.com/BseIndiaAPI/api"
BSE_WEB = "https://www.bseindia.com"

CACHE_DIR = BACKEND_DIR / "data" / "cache"

# Politeness: never hammer the exchanges.
_REQUEST_DELAY_SECONDS = 0.35
_BSE_REQUEST_DELAY_SECONDS = 0.8
_LAST_REQUEST_AT = 0.0


class SourceUnavailable(Exception):
    """Raised when an official source cannot be reached or parsed."""


# ---------------------------------------------------------------------------
# HTTP plumbing
# ---------------------------------------------------------------------------

def _throttle(min_interval: float) -> None:
    global _LAST_REQUEST_AT
    wait = min_interval - (time.time() - _LAST_REQUEST_AT)
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST_AT = time.time()


def _http_get(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 90,
    retries: int = 3,
    opener: Optional[urllib.request.OpenerDirector] = None,
) -> bytes:
    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
    if headers:
        hdrs.update(headers)
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        _throttle(_REQUEST_DELAY_SECONDS)
        try:
            req = urllib.request.Request(url, headers=hdrs)
            if opener is not None:
                with opener.open(req, timeout=timeout) as resp:
                    return resp.read()
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in (403, 429):
                time.sleep(1.5 * attempt)
            elif exc.code >= 500:
                time.sleep(1.0 * attempt)
            else:
                raise SourceUnavailable(f"HTTP {exc.code} for {url}") from exc
        except Exception as exc:  # network, timeout, DNS
            last_exc = exc
            time.sleep(1.0 * attempt)
    raise SourceUnavailable(f"request failed for {url}: {last_exc}")


def _cache_path(*parts: str) -> Path:
    path = CACHE_DIR.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _cached(key_parts: Sequence[str], fetch) -> bytes:
    path = _cache_path(*key_parts)
    if path.exists() and path.stat().st_size > 0:
        return path.read_bytes()
    data = fetch()
    if data:
        path.write_bytes(data)
    return data


# ---------------------------------------------------------------------------
# Small parsing helpers
# ---------------------------------------------------------------------------

def _clean(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\ufeff", "").strip()


def _num(value, default: Optional[float] = None) -> Optional[float]:
    text = _clean(value).replace(",", "")
    if text in ("", "-", "--", "NA", "N/A", "null", "None"):
        return default
    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def _int(value, default: int = 0) -> int:
    number = _num(value)
    return int(number) if number is not None else default


def _csv_rows(text: str) -> List[Dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    out: List[Dict[str, str]] = []
    for raw in reader:
        row = {_clean(k): _clean(v) for k, v in raw.items() if k is not None}
        if any(row.values()):
            out.append(row)
    return out


def _parse_date(text: str) -> Optional[date]:
    text = _clean(text)
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[: len(fmt) + 6], fmt).date()
        except ValueError:
            continue
    return None


def _file_session(rows: Sequence[Dict[str, str]], keys: Sequence[str]) -> Optional[date]:
    """Session date carried inside an archive file, when it has one."""
    for row in rows[:5]:
        for key in keys:
            parsed = _parse_date(row.get(key, ""))
            if parsed:
                return parsed
    return None


def _require_session(rows: Sequence[Dict[str, str]], keys: Sequence[str], expected: date, label: str) -> None:
    """Reject a file whose own date does not match the requested session.

    The NSE archive answers a holiday request with the previous session's file
    instead of a 404.  Without this check those rows would be stored under the
    holiday date and duplicate an existing session.
    """
    found = _file_session(rows, keys)
    if found is not None and found != expected:
        raise SourceUnavailable(
            f"{label} requested for {expected.isoformat()} contains {found.isoformat()} data"
        )


def _month_dir(d: date) -> str:
    return d.strftime("%b").upper()


# ---------------------------------------------------------------------------
# Trading calendar
# ---------------------------------------------------------------------------

_HOLIDAY_CACHE: Dict[int, set] = {}

# NSE holds a one-hour Muhurat session on Diwali Laxmi Pujan even when the date
# falls on a weekend (e.g. Sunday 8 Nov 2026). The holiday master lists that
# date as a holiday, so the confirmed special session is added back explicitly.
SPECIAL_SESSIONS = {date(2026, 11, 8)}


def nse_holidays(year: int) -> set:
    """NSE trading holidays (CM segment) for a year; empty when unavailable."""
    if year in _HOLIDAY_CACHE:
        return _HOLIDAY_CACHE[year]

    def fetch() -> bytes:
        url = f"{NSE_WEB}/api/holiday-master?type=trading"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{NSE_WEB}/",
            "Origin": NSE_WEB,
        }
        return _http_get(url, headers=headers, timeout=45)

    holidays: set = set()
    try:
        payload = json.loads(_cached(("nse", f"holidays_{year}.json"), fetch).decode("utf-8", "replace"))
        for item in payload.get("CM", []):
            parsed = _parse_date(item.get("tradingDate", ""))
            if parsed and parsed.year == year:
                holidays.add(parsed)
    except Exception as exc:  # noqa: BLE001 - holidays are best effort
        logger.debug("NSE holiday calendar unavailable for %s: %s", year, exc)
    _HOLIDAY_CACHE[year] = holidays
    return holidays


def trading_days(start: date, end: date) -> List[date]:
    """Weekdays between start and end that are not NSE trading holidays."""
    if start > end:
        return []
    holidays: set = set()
    for year in range(start.year, end.year + 1):
        holidays |= nse_holidays(year)
    out: List[date] = []
    cur = start
    while cur <= end:
        if cur in SPECIAL_SESSIONS or (cur.weekday() < 5 and cur not in holidays):
            out.append(cur)
        cur += timedelta(days=1)
    return out


# ---------------------------------------------------------------------------
# NSE
# ---------------------------------------------------------------------------

def nse_equity_master() -> List[Dict[str, str]]:
    """Official NSE equity master (EQUITY_L.csv)."""
    url = f"{NSE_ARCHIVE}/content/equities/EQUITY_L.csv"

    def fetch() -> bytes:
        return _http_get(url, headers={"Referer": f"{NSE_WEB}/"})

    text = _cached(("nse", "EQUITY_L.csv"), fetch).decode("utf-8-sig", "replace")
    out = []
    for row in _csv_rows(text):
        symbol = _clean(row.get("SYMBOL"))
        if not symbol:
            continue
        out.append(
            {
                "symbol": symbol,
                "name": _clean(row.get("NAME OF COMPANY")),
                "series": _clean(row.get("SERIES")),
                "listing_date": _clean(row.get("DATE OF LISTING")),
                "isin": _clean(row.get("ISIN NUMBER")),
                "face_value": _num(row.get("FACE VALUE")),
            }
        )
    return out


def nse_index_constituents(filename: str) -> List[Dict[str, str]]:
    """Constituent list such as ``ind_nifty50list.csv``."""
    url = f"{NSE_ARCHIVE}/content/indices/{filename}"

    def fetch() -> bytes:
        return _http_get(url, headers={"Referer": f"{NSE_WEB}/"})

    text = _cached(("nse", "indices", filename), fetch).decode("utf-8-sig", "replace")
    out = []
    for row in _csv_rows(text):
        symbol = _clean(row.get("Symbol"))
        if not symbol:
            continue
        out.append(
            {
                "symbol": symbol,
                "name": _clean(row.get("Company Name")),
                "industry": _clean(row.get("Industry")),
                "series": _clean(row.get("Series")),
                "isin": _clean(row.get("ISIN Code")),
            }
        )
    return out


def nse_bhavcopy_udiff(d: date) -> List[Dict]:
    """NSE UDiFF daily bhavcopy (compact zip) for a session."""
    stamp = d.strftime("%Y%m%d")
    url = f"{NSE_ARCHIVE}/content/cm/BhavCopy_NSE_CM_0_0_0_{stamp}_F_0000.csv.zip"

    def fetch() -> bytes:
        return _http_get(url, headers={"Referer": f"{NSE_WEB}/"})

    raw = _cached(("nse", "udiff", f"{stamp}.zip"), fetch)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            name = archive.namelist()[0]
            text = archive.read(name).decode("utf-8-sig", "replace")
    except Exception as exc:
        raise SourceUnavailable(f"NSE UDiFF bhavcopy {stamp} unreadable: {exc}") from exc
    return _parse_nse_udiff(text, d)


def _parse_nse_udiff(text: str, d: date) -> List[Dict]:
    rows = _csv_rows(text)
    _require_session(rows, ("TradDt",), d, "NSE UDiFF bhavcopy")
    out = []
    for row in rows:
        if _clean(row.get("Sgmt")) != "CM":
            continue
        series = _clean(row.get("SctySrs"))
        if series not in ("EQ", "BE", "BZ"):
            continue
        symbol = _clean(row.get("TckrSymb"))
        close = _num(row.get("ClsPric"))
        if not symbol or close is None or close <= 0:
            continue
        out.append(
            {
                "symbol": symbol,
                "series": series,
                "date": d.isoformat(),
                "open": _num(row.get("OpnPric"), close),
                "high": _num(row.get("HghPric"), close),
                "low": _num(row.get("LwPric"), close),
                "close": close,
                "last": _num(row.get("LastPric"), close),
                "prev_close": _num(row.get("PrvsClsgPric"), close),
                "volume": _int(row.get("TtlTradgVol")),
                "turnover": _num(row.get("TtlTrfVal"), 0.0),
                "trades": _int(row.get("TtlNbOfTxsExctd")),
                "deliverable_qty": None,
                "deliverable_pct": None,
                "isin": _clean(row.get("ISIN")),
                "source": "nse",
            }
        )
    return out


def nse_bhavcopy_full(d: date) -> List[Dict]:
    """NSE full bhavcopy (includes delivery data) for a session."""
    stamp = d.strftime("%d%m%Y")
    url = f"{NSE_ARCHIVE}/products/content/sec_bhavdata_full_{stamp}.csv"

    def fetch() -> bytes:
        return _http_get(url, headers={"Referer": f"{NSE_WEB}/"})

    text = _cached(("nse", "full", f"{stamp}.csv"), fetch).decode("utf-8-sig", "replace")
    rows = _csv_rows(text)
    _require_session(rows, ("DATE1",), d, "NSE full bhavcopy")
    out = []
    for row in rows:
        series = _clean(row.get("SERIES"))
        if series not in ("EQ", "BE", "BZ"):
            continue
        symbol = _clean(row.get("SYMBOL"))
        close = _num(row.get("CLOSE_PRICE"))
        if not symbol or close is None or close <= 0:
            continue
        out.append(
            {
                "symbol": symbol,
                "series": series,
                "date": d.isoformat(),
                "open": _num(row.get("OPEN_PRICE"), close),
                "high": _num(row.get("HIGH_PRICE"), close),
                "low": _num(row.get("LOW_PRICE"), close),
                "close": close,
                "last": _num(row.get("LAST_PRICE"), close),
                "prev_close": _num(row.get("PREV_CLOSE"), close),
                "volume": _int(row.get("TTL_TRD_QNTY")),
                "turnover": _num(row.get("TURNOVER_LACS"), 0.0),
                "trades": _int(row.get("NO_OF_TRADES")),
                "deliverable_qty": _num(row.get("DELIV_QTY")),
                "deliverable_pct": _num(row.get("DELIV_PER")),
                "isin": "",
                "source": "nse",
            }
        )
    return out


def nse_bhavcopy(d: date) -> List[Dict]:
    """Best available NSE bhavcopy for a session.

    Uses the compact UDiFF file first (available for recent years) and falls
    back to the full bhavcopy, then to the legacy archive zip.
    """
    errors = []
    for loader in (nse_bhavcopy_udiff, nse_bhavcopy_full):
        try:
            rows = loader(d)
            if rows:
                return rows
        except SourceUnavailable as exc:
            errors.append(str(exc))
    try:
        rows = nse_bhavcopy_legacy(d)
        if rows:
            return rows
    except SourceUnavailable as exc:
        errors.append(str(exc))
    raise SourceUnavailable(f"no NSE bhavcopy for {d.isoformat()}: {'; '.join(errors[-2:])}")


def nse_bhavcopy_legacy(d: date) -> List[Dict]:
    """Legacy NSE archive bhavcopy zip (1995-2020)."""
    url = (
        f"{NSE_ARCHIVE}/content/historical/EQUITIES/{d.year}/{_month_dir(d)}/"
        f"cm{d.strftime('%d%b%Y').upper()}bhav.csv.zip"
    )

    def fetch() -> bytes:
        return _http_get(url, headers={"Referer": f"{NSE_WEB}/"})

    raw = _cached(("nse", "legacy", f"{d.strftime('%Y%m%d')}.zip"), fetch)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        text = archive.read(archive.namelist()[0]).decode("utf-8", "replace")
    out = []
    for row in _csv_rows(text):
        series = _clean(row.get("SERIES"))
        if series not in ("EQ", "BE", "BZ"):
            continue
        symbol = _clean(row.get("SYMBOL"))
        close = _num(row.get("CLOSE"))
        if not symbol or close is None or close <= 0:
            continue
        out.append(
            {
                "symbol": symbol,
                "series": series,
                "date": d.isoformat(),
                "open": _num(row.get("OPEN"), close),
                "high": _num(row.get("HIGH"), close),
                "low": _num(row.get("LOW"), close),
                "close": close,
                "last": _num(row.get("LAST"), close),
                "prev_close": _num(row.get("PREVCLOSE"), close),
                "volume": _int(row.get("TOTTRDQTY")),
                "turnover": _num(row.get("TOTTRDVAL"), 0.0),
                "trades": _int(row.get("TOTALTRADES")),
                "deliverable_qty": None,
                "deliverable_pct": None,
                "isin": _clean(row.get("ISIN")),
                "source": "nse",
            }
        )
    return out


def nse_index_close(d: date) -> List[Dict]:
    """NSE end-of-day close for all indices published for a session."""
    stamp = d.strftime("%d%m%Y")
    url = f"{NSE_ARCHIVE}/content/indices/ind_close_all_{stamp}.csv"

    def fetch() -> bytes:
        return _http_get(url, headers={"Referer": f"{NSE_WEB}/"})

    text = _cached(("nse", "indices_close", f"{stamp}.csv"), fetch).decode("utf-8-sig", "replace")
    rows = _csv_rows(text)
    _require_session(rows, ("Index Date",), d, "NSE index close file")
    out = []
    for row in rows:
        name = _clean(row.get("Index Name"))
        close = _num(row.get("Closing Index Value"))
        if not name or close is None or close <= 0:
            continue
        out.append(
            {
                "name": name,
                "date": d.isoformat(),
                "open": _num(row.get("Open Index Value"), close),
                "high": _num(row.get("High Index Value"), close),
                "low": _num(row.get("Low Index Value"), close),
                "close": close,
                "change_points": _num(row.get("Points Change")),
                "change_pct": _num(row.get("Change(%)")),
                "volume": _int(row.get("Volume")),
                "turnover": _num(row.get("Turnover (Rs. Cr.)"), 0.0),
                "pe": _num(row.get("P/E")),
                "pb": _num(row.get("P/B")),
                "div_yield": _num(row.get("Div Yield")),
                "source": "nse",
            }
        )
    return out


# ---------------------------------------------------------------------------
# BSE
# ---------------------------------------------------------------------------

_BSE_OPENER: Optional[urllib.request.OpenerDirector] = None
_BSE_PRIMED_AT = 0.0
_BSE_COOKIE_JAR = http.cookiejar.CookieJar()


def _bse_opener() -> urllib.request.OpenerDirector:
    global _BSE_OPENER
    if _BSE_OPENER is None:
        _BSE_OPENER = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(_BSE_COOKIE_JAR)
        )
    return _BSE_OPENER


def _bse_prime(force: bool = False) -> None:
    global _BSE_PRIMED_AT
    if not force and (time.time() - _BSE_PRIMED_AT) < 240:
        return
    opener = _bse_opener()
    page_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        _http_get(f"{BSE_WEB}/", headers=page_headers, timeout=45, opener=opener)
        time.sleep(0.6)
        _http_get(
            f"{BSE_WEB}/Indices/IndexArchiveData.html",
            headers={**page_headers, "Referer": f"{BSE_WEB}/"},
            timeout=45,
            opener=opener,
        )
        _BSE_PRIMED_AT = time.time()
    except Exception as exc:  # noqa: BLE001
        logger.debug("BSE cookie priming failed: %s", exc)


def _bse_get_json(path: str, params: Optional[Dict[str, str]] = None) -> Dict:
    url = f"{BSE_API}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    api_headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"{BSE_WEB}/Indices/IndexArchiveData.html",
        "Origin": BSE_WEB,
        "X-Requested-With": "XMLHttpRequest",
    }
    last_exc: Optional[Exception] = None
    for attempt in range(1, 4):
        _bse_prime(force=attempt > 1)
        _throttle(_BSE_REQUEST_DELAY_SECONDS)
        try:
            raw = _http_get(url, headers=api_headers, timeout=90, retries=1, opener=_bse_opener())
            return json.loads(raw.decode("utf-8", "replace"))
        except SourceUnavailable as exc:
            last_exc = exc
            time.sleep(1.5 * attempt)
        except json.JSONDecodeError as exc:
            last_exc = exc
            time.sleep(1.0 * attempt)
    raise SourceUnavailable(f"BSE request failed for {path}: {last_exc}")


def bse_scrip_master() -> List[Dict]:
    """Official BSE active equity scrip master."""
    def fetch() -> bytes:
        payload = _bse_get_json(
            "ListofScripData/w",
            {"Group": "", "Scripcode": "", "industry": "", "segment": "Equity", "status": "Active"},
        )
        return json.dumps(payload).encode("utf-8")

    payload = json.loads(_cached(("bse", "scrip_master.json"), fetch).decode("utf-8", "replace"))
    out = []
    for row in payload:
        code = _clean(row.get("SCRIP_CD") or row.get("scripcode") or row.get("Scripcode"))
        if not code:
            continue
        out.append(
            {
                "scrip_code": code,
                "ticker": _clean(row.get("scrip_id") or row.get("Scrip_id")),
                "name": _clean(row.get("Scrip_Name") or row.get("scrip_name")),
                "isin": _clean(row.get("ISIN_NUMBER") or row.get("ISIN")),
                "group": _clean(row.get("GROUP") or row.get("Group")),
                "industry": _clean(row.get("INDUSTRY") or row.get("Industry")),
                "market_cap": _num(row.get("Mktcap") or row.get("MKTCAP")),
            }
        )
    return out


def bse_bhavcopy(d: date) -> List[Dict]:
    """BSE UDiFF bhavcopy for a session (2024 onwards)."""
    stamp = d.strftime("%Y%m%d")
    url = (
        f"{BSE_WEB}/download/BhavCopy/Equity/"
        f"BhavCopy_BSE_CM_0_0_0_{stamp}_F_0000.CSV"
    )

    def fetch() -> bytes:
        return _http_get(url, headers={"Referer": f"{BSE_WEB}/"})

    text = _cached(("bse", "udiff", f"{stamp}.csv"), fetch).decode("utf-8-sig", "replace")
    out = []
    for row in _csv_rows(text):
        if _clean(row.get("Sgmt")) != "CM":
            continue
        series = _clean(row.get("SctySrs"))
        if series != "STK":
            continue
        ticker = _clean(row.get("TckrSymb"))
        close = _num(row.get("ClsPric"))
        if not ticker or close is None or close <= 0:
            continue
        out.append(
            {
                "ticker": ticker,
                "scrip_code": _clean(row.get("FinInstrmId")),
                "isin": _clean(row.get("ISIN")),
                "series": series,
                "date": d.isoformat(),
                "open": _num(row.get("OpnPric"), close),
                "high": _num(row.get("HghPric"), close),
                "low": _num(row.get("LwPric"), close),
                "close": close,
                "prev_close": _num(row.get("PrvsClsgPric"), close),
                "volume": _int(row.get("TtlTradgVol")),
                "turnover": _num(row.get("TtlTrfVal"), 0.0),
                "trades": _int(row.get("TtlNbOfTxsExctd")),
                "source": "bse",
            }
        )
    return out


def bse_index_history(name: str, start: date, end: date) -> List[Dict]:
    """BSE index daily OHLC archive for a single index and date range."""
    params = {
        "fmdt": start.strftime("%d/%m/%Y"),
        "index": name,
        "period": "D",
        "todt": end.strftime("%d/%m/%Y"),
    }
    key = ("bse", "index", f"{name.replace(' ', '_')}_{start:%Y%m%d}_{end:%Y%m%d}.json")
    payload = json.loads(
        _cached(key, lambda: json.dumps(_bse_get_json("IndexArchDailyPAR/w", params)).encode("utf-8")).decode("utf-8")
    )
    rows = payload.get("Table") or []
    out = []
    for row in rows:
        parsed = _parse_date(row.get("tdate") or row.get("date") or "")
        close = _num(row.get("I_close"))
        if not parsed or close is None or close <= 0:
            continue
        out.append(
            {
                "name": _clean(row.get("I_name")) or name,
                "date": parsed.isoformat(),
                "open": _num(row.get("I_open"), close),
                "high": _num(row.get("I_high"), close),
                "low": _num(row.get("I_low"), close),
                "close": close,
                "change_pct": _num(row.get("ChgPer")),
                "change_points": _num(row.get("Chg")),
                "prev_close": _num(row.get("Prev_Close")),
                "pe": _num(row.get("I_pe")),
                "pb": _num(row.get("I_pb")),
                "div_yield": _num(row.get("I_yl")),
                "volume": _num(row.get("Volume")),
                "turnover": _num(row.get("Turnover")),
                "source": "bse",
            }
        )
    out.sort(key=lambda r: r["date"])
    return out


def bse_all_indices(d: date) -> List[Dict]:
    """Every BSE index published for one session."""
    params = {
        "fmdt": d.strftime("%d/%m/%Y"),
        "index": "All",
        "period": "D",
        "todt": d.strftime("%d/%m/%Y"),
    }
    key = ("bse", "all_indices", f"{d:%Y%m%d}.json")
    payload = json.loads(
        _cached(key, lambda: json.dumps(_bse_get_json("IndexArchDailyAllPar/w", params)).encode("utf-8")).decode("utf-8")
    )
    rows = payload.get("Table") or []
    out = []
    for row in rows:
        parsed = _parse_date(row.get("date") or row.get("tdate") or "")
        close = _num(row.get("I_close"))
        name = _clean(row.get("I_name"))
        if not parsed or close is None or close <= 0 or not name:
            continue
        out.append(
            {
                "name": name,
                "date": parsed.isoformat(),
                "open": _num(row.get("I_open"), close),
                "high": _num(row.get("I_high"), close),
                "low": _num(row.get("I_low"), close),
                "close": close,
                "change_pct": _num(row.get("ChgPer")),
                "change_points": _num(row.get("Chg")),
                "prev_close": _num(row.get("Prev_Close")),
                "pe": _num(row.get("I_pe")),
                "pb": _num(row.get("I_pb")),
                "div_yield": _num(row.get("I_yl")),
                "volume": _num(row.get("Volume")),
                "turnover": _num(row.get("Turnover")),
                "source": "bse",
            }
        )
    return out


# ---------------------------------------------------------------------------
# Live / latest-session snapshots
# ---------------------------------------------------------------------------

def nse_all_indices() -> List[Dict]:
    """NSE live index snapshot (advances/declines included when available)."""
    url = f"{NSE_WEB}/api/allIndices"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{NSE_WEB}/",
        "Origin": NSE_WEB,
    }
    payload = json.loads(_http_get(url, headers=headers, timeout=45).decode("utf-8", "replace"))
    out = []
    for row in payload.get("data", []):
        name = _clean(row.get("index"))
        last = _num(row.get("last"))
        if not name or last is None or last <= 0:
            continue
        out.append(
            {
                "name": name,
                "close": last,
                "open": _num(row.get("open"), last),
                "high": _num(row.get("high"), last),
                "low": _num(row.get("low"), last),
                "prev_close": _num(row.get("previousClose"), last),
                "change_pct": _num(row.get("percentChange")),
                "change_points": _num(row.get("variation")),
                "volume": _int(row.get("totalTradedVolume")),
                "advances": _int(row.get("advances")),
                "declines": _int(row.get("declines")),
                "unchanged": _int(row.get("unchanged")),
                "timestamp": _clean(row.get("timeVal")),
                "source": "nse",
            }
        )
    return out
