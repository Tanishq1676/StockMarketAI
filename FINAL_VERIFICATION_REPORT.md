# Final Verification Report — Official NSE/BSE Data

**Project:** IndStock Intelligence (Stock Market Intelligence Platform)
**Verification date:** Monday, 23 November 2026
**Latest completed session:** **Friday, 20 November 2026**
**Last data fetch:** **23 November 2026, 14:17:17 UTC** (07:47:17 pm IST)
**Price basis:** latest official exchange close — **not live intraday**
**Demo/synthetic rows in database:** **0**

---

## 1. Executive summary

| Item | Result |
|---|---|
| Active stock universe | **497** NSE equities (official NIFTY 500 constituents, EQ/BE/BZ series) |
| Latest quote rows | **532** = 497 stocks + 30 NSE indices + 5 BSE indices |
| Latest quote session | **2026-11-20** for every row |
| `is_live` rows | **0** (all rows are official EOD closes) |
| History rows | **250,758** (2024-11-21 → 2026-11-20) |
| NSE stock sessions | **495** (plus 3 official BSE weekend sessions) |
| Duplicate rows | **0** across all tables |
| Non-official / demo rows | **0** across `market_data`, `historical_price`, `index_history` |
| Latest price vs. history mismatch | **0** |
| Null / zero prices | **0** |
| Missing `prev_close` | **0** |
| Signals | **497** (one per active stock, all with reasons) |
| Predictions | **138** (23 symbols × 6 horizons) |
| Daily reports | **1** (session 2026-11-20) |
| Frontend routes verified | **9 / 9 return HTTP 200, zero console errors** |

---

## 2. Stocks updated (latest session)

All 497 active symbols carry a verified 20-Nov-2026 close, previous close, open/high/low, volume, trade date, fetch timestamp and source URL.

Representative verified values:

| Symbol | Close | Prev. close | Change % | Trade date |
|---|---:|---:|---:|---|
| RELIANCE | 1,377.50 | 1,375.60 | +0.138% | 2026-11-20 |
| TCS | 2,376.20 | 2,342.70 | +1.430% | 2026-11-20 |
| HDFCBANK | 846.00 | 821.80 | +2.945% | 2026-11-20 |
| INFY | 1,098.00 | 1,091.90 | +0.559% | 2026-11-20 |

Indices:

| Index | Close | Prev. close | Change % | Trade date |
|---|---:|---:|---:|---|
| NIFTY 50 | 25,800.60 | 25,514.30 | +1.120% | 2026-11-20 |
| NIFTY BANK | 64,635.20 | 63,063.00 | +2.490% | 2026-11-20 |
| SENSEX | 83,919.71 | — | +1.082% | 2026-11-20 |
| BANKEX | 72,696.05 | — | +2.338% | 2026-11-20 |

`change_pct` is stored as a **percentage** everywhere. The full range is −5.702% to +8.5909%.
Recomputing `(close − prev_close) / prev_close × 100` from the stored closes differs by at most **0.0048 percentage points**, and only for index rows, because NSE publishes index change rounded to 2 decimals. Stock rows match exactly.

---

## 3. Latest trading date and timestamps

- **Latest trading date:** Friday, **20 November 2026** (NSE and BSE).
- **Saturday 21 November 2026:** weekend — no session.
- **Current date:** Monday, 23 November 2026.
- **Last fetch:** `2026-11-23T14:17:17.647380Z` (all 532 quote rows share this timestamp).
- Frontend renders it as **“Fetched 23 Nov 2026, 07:47 pm IST”** and labels the price **“Latest close”**, with the banner **“Latest closing prices (not live intraday)”**.
- The most recent `IngestRun` is id **9**, `ingest_eod`, status **completed**, 532 rows fetched, latest trade date `2026-11-20`.

---

## 4. History coverage

| Dataset | Rows | Symbols | Date range |
|---|---:|---:|---|
| NSE stocks (`historical_price.source='nse'`) | 235,792 | 497 | 2024-11-21 → 2026-11-20 |
| NSE indices (`nse-index`) | 14,465 | 30 | 2024-11-21 → 2026-11-20 |
| BSE indices (`bse-index`) | 501 | 5 | 2024-11-21 → 2026-11-20 |
| **Total `historical_price`** | **250,758** | 532 | 2024-11-21 → 2026-11-20 |
| **`index_history`** | **14,966** | 35 | 2024-11-21 → 2026-11-20 |

- **495** NSE stock sessions and **495** NSE index sessions; the two date sets are identical.
- Median and maximum per-symbol coverage are **495 sessions**.
- 29 symbols have fewer than 300 rows because they listed after November 2024. The only symbols below 100 rows are **ICICILIFE** (21 rows, listed 2026-10-23) and **HEGAM** (42 rows, listed 2026-09-22).
- **NIFTYCAPITALGOODS** starts 2026-06-15 (110 sessions) — the index was launched then; older values are not published by NSE.
- **BANKEX, BSE100, BSE200, BSE500** have only the 2026-11-20 session because BSE’s all-indices endpoint publishes one day at a time. **SENSEX** has the full range (497 sessions, including three official weekend rows).

---

## 5. Records changed in this verification pass

### Latest quotes
- **532** quote rows refreshed (497 NSE stocks + 30 NSE indices + 5 BSE indices) at `2026-11-23T14:17:17Z`.

### History repairs
| Change | Rows |
|---|---:|
| Removed stale duplicate sessions: 2024-12-25, 2025-10-22, 2025-11-05 | **1,404** |
| Added official **Muhurat session 2026-11-08**: 497 stocks + 29 indices | **526** |
| Backfilled missed session **2024-12-18** (transient DNS failure during the original backfill) | **450** |
| Refreshed 2024-12-19 (correct `prev_close` after 18-Dec insert) | 451 |
| Refreshed 2026-11-09 (correct `prev_close` after 08-Nov insert) | 497 stocks + 30 indices |

The three removed dates were NSE holidays. The archive answered those requests with the **previous session’s file** (identical closes and volumes for 100% of symbols), which had created duplicate sessions. This is now blocked at the parser level (see §8).

### Derived data regenerated
- **497** signals (389 WAIT_FOR_CONFIRMATION, 69 BUY, 20 SELL, 19 HOLD), all carrying reasons and summaries.
- **138** predictions across 23 symbols (15m, 30m, 1h, 2h, 1d, 5d).
- **1** daily report for session 2026-11-20 with session date, fetch timestamp, official sources and `price_basis=latest_official_close`.

### Test-artifact cleanup
`transactions`, `paper_positions`, `paper_trades`, `alerts`, `news_articles` are all **0**. The news feed is intentionally empty — no fabricated headlines.

---

## 6. Integrity checks

| Check | Result |
|---|---|
| Duplicate `(symbol, trade_date)` in `market_data` | 0 |
| Duplicate `(symbol, date, source)` in `historical_price` | 0 |
| Duplicate `(symbol, date)` in `index_history` | 0 |
| Sessions that duplicate the prior session (>50% identical close+volume) | 0 |
| Quote rows without matching history on the trade date | 0 |
| Quote price ≠ history close on the trade date | 0 |
| `market_data` rows with null/zero OHLC | 0 |
| `market_data` rows with null `prev_close` | 0 |
| `historical_price` rows with null/zero close | 0 |
| `index_history` rows with null/zero close or null `pct_change` | 0 |
| Non-official source values | 0 |
| `is_live = true` | 0 |

Every quote row also carries `source_url`, `fetched_at`, `trade_date` and `is_live=false`, so the UI can always distinguish latest close from live.

---

## 7. Sources used (official only)

### NSE
- Equity master: `https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv`
- Full bhavcopy: `https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv`
- UDiFF bhavcopy: `https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip`
- Legacy bhavcopy (fallback): `https://nsearchives.nseindia.com/content/historical/EQUITIES/...`
- Index close: `https://nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv`
- Holiday master: `https://www.nseindia.com/api/holiday-master?type=trading`
- Index constituents: `https://nsearchives.nseindia.com/content/indices/ind_nifty*list.csv`

### BSE
- Scrip master: `https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w`
- UDiFF bhavcopy
- SENSEX range archive: `IndexArchDailyPAR`
- Latest all-indices snapshot: `IndexArchDailyAllPar`

Sources stored in the database: `market_data` → `nse` (497), `nse-index` (30), `bse-index` (5); `historical_price` → `nse`, `nse-index`, `bse-index`; `index_history` → `nse`, `bse`.

---

## 8. Backend fixes made during verification

1. **Stale archive-file rejection** (`backend/app/data/official.py`): `_require_session()` checks the session date carried inside each NSE file (`TradDt`, `DATE1`, `Index Date`). A file for another session is rejected instead of being stored under the requested holiday date. This is the root-cause fix for the three duplicate holiday sessions.
2. **Muhurat sessions** (`official.py`): `SPECIAL_SESSIONS = {2026-11-08}` adds the confirmed Sunday Diwali Muhurat session back into the trading calendar (the holiday master lists it as a holiday).
3. **Sector performance** (`backend/app/reports/helpers.py`): replaced one query per symbol with a single grouped read plus a 10-minute in-process cache; dashboard composition dropped from ~7.3 s to ~0.16 s on repeat.
4. **Unusual volume** (`helpers.py`, `SnapshotTable.tsx`): now compares session volume with the 60-session average and shows the real multiple (e.g. NUVOCO 31.5×), instead of reusing “most active”.
5. **Watchlist** (`Watchlist.tsx`, `stock_routes.py`): quotes are fetched only for the saved symbols via `/api/stocks?symbols=...`; the 500-row catalogue is used only for add-symbol suggestions.
6. **Report metadata** (`reports/page.tsx`): source labels are deduplicated (`BSE official · NSE official`), alongside session date and fetch timestamp.
7. **Signal ordering** (`signals/engine.py`): `/api/signals` orders by confidence then recency; scheduler no longer writes duplicate signal rows.
8. **Rules engine** (`ai/rules_engine.py`): moving averages are read from the nested `technical.ma` structure, so all 497 signals now carry reasons.

---

## 9. Missing data and limitations (disclosed)

1. **No free official real-time equity quotes.** NSE `quote-equity` returns 403, `equity-stockIndices` 404, `historical/cm/equity` 503, `chart-databyindex` empty. The platform therefore serves **latest official closes**, explicitly labelled `is_live=false`. It never presents a historical close as live.
2. **No deep intraday history.** Free official archives provide EOD only; BSE’s intraday endpoint gives a single latest session. Intraday charts are out of scope for this dataset.
3. **NIFTYCAPITALGOODS** history begins 2026-06-15 (index launch), 110 sessions.
4. **BANKEX, BSE100, BSE200, BSE500** have only the 2026-11-20 session.
5. **Recent listings** explain all short histories: ICICILIFE 21 rows, HEGAM 42, VAML/VEDPOWER/VISL/VOGL 110 each (listed 2026-06-15), and 24 more symbols with 160–292 rows.
6. **NSE holiday master covers 2026 only.** For 2024/2025, holidays are detected from missing archive files and now also from the file’s own session date. This is why the three stale holiday files were caught.
7. **Three official BSE SENSEX weekend rows are retained** because BSE published them:
   - 2025-02-01 (Saturday Budget session)
   - 2026-02-01 (BSE-published Sunday row, unexplained by BSE)
   - 2026-11-08 (Sunday Diwali Muhurat session)
8. **News feed is empty by design.** No free official headline feed is configured, and no headlines are fabricated.

---

## 10. Frontend confirmation

All routes were rendered in the in-app browser against the production build:

| Route | HTTP | Verified content |
|---|---|---|
| `/` | 200 | NIFTY 50 25,800.6 (+1.12%), SENSEX 83,919.71 (+1.08%), BANK NIFTY 64,635.2 (+2.49%), “Session Fri, 20 Nov, 2026”, “Fetched 23 Nov 2026, 07:47 pm IST”, “Latest closing prices (not live intraday)” |
| `/stocks` | 200 | “497 tracked”, all rows dated 20 Nov 2026, “Latest close” |
| `/stocks/RELIANCE` | 200 | ₹1,377.5, prev. close 1,375.6, +0.14%, “Session Fri, 20 Nov, 2026”, “NSE official” |
| `/stocks/NIFTY50` | 200 | ₹25,800.6, prev. 25,514.3, +1.12%, “NSE official” |
| `/reports` | 200 | Session 20 Nov 2026, fetch timestamp, “BSE official · NSE official”, “6 tracked indices — all advancing” |
| `/alerts` | 200 | “No active alerts” |
| `/news` | 200 | “No headlines cached right now” |
| `/paper-trading` | 200 | ₹1,00,000 wallet, “No open positions” |
| `/portfolio` | 200 | “No holdings”, ₹0, 0.00% |

- **0 console errors** on every page.
- **No** “demo”, “synthetic”, `NaN` or `undefined` strings in rendered output.
- Dashboard watchlist shows live DB prices: RELIANCE ₹1,377.5, TCS ₹2,376.2, HDFCBANK ₹846, INFY ₹1,098, all dated 20 Nov 2026.
- Unusual-volume panel shows real multiples (NUVOCO 31.5×, EIHOTEL 16.4×, INDUSINDBK 8.7×).
- `npx tsc --noEmit` passed; `next build` produced 9 routes successfully.

---

## 11. Running services

| Service | URL | Status |
|---|---|---|
| Backend (FastAPI) | `http://127.0.0.1:8000` | healthy — `demo_mode=false`, `official_data=true` |
| Frontend (Next.js) | `http://127.0.0.1:3000` | serving production build |

Health payload:
```json
{"status":"ok","service":"indian-stock-market-intelligence",
 "data_sources":["bse-index","nse","nse-index"],
 "demo_mode":false,"official_data":true}
```

---

## 12. Reproducibility

- Backfill window: **2024-11-21 → 2026-11-20** (configurable).
- `IngestRun` audit trail: 9 runs, including the two `repair_sessions` entries and the final `ingest_eod` (id 9).
- Raw downloads are cached under `backend/data/cache/`; database at `backend/data/app.db`.
- Ingestion is idempotent: a date range is replaced, not appended; file-date validation prevents a stale archive file from creating a duplicate session.
