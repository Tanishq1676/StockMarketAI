# 📈 Indian Stock Market Intelligence Platform (AI-Powered)

A production-grade, AI-powered research assistant for **all NSE and BSE listed equities**. Analyzes five years of historical market data, generates technical indicators, forecasts short-term price movements, produces AI market commentary (via local Ollama), aggregates financial news with sentiment analysis, and offers BUY/SELL/HOLD decision support, portfolio management and paper trading — all on a professional terminal-style dark dashboard.

**Demo mode out of the box.** Without data-provider credentials, the platform ships a fully functional **clearly-labelled demo data source** (`data_source="demo"` on every row) generating realistic synthetic market series.

---

## 1. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS |
| Charts | TradingView Lightweight Charts (candlestick + MA overlays) |
| Backend | FastAPI (Python), uvicorn, SQLAlchemy, Pydantic |
| Database | PostgreSQL (default) — SQLite supported via `DATABASE_URL` |
| AI | Ollama (local, e.g. `llama3.1:8b`) via `OLLAMA_URL`/`OLLAMA_MODEL` |
| Data processing | Pandas, NumPy, Scikit-learn |
| Technical analysis | TA-Lib-equivalent functions (own indicators module) |
| Jobs | APScheduler (or asyncio fallback) |
| Live updates | WebSocket `/api/ws/market-updates` (60 s refresh) |
| Deployment | Vercel (frontend), backend host (e.g. uvicorn + WSGI/proxy) |

## 2. Architecture

```
frontend/                Next.js dashboard + chart + search + portfolio + paper trading UI
backend/app/
  main.py                FastAPI app + startup (DB init, seed, scheduler)
  config.py              Env config (API keys, Ollama, DB, defaults)
  database.py            SQLAlchemy engine + session
  models.py              Tables: stock_meta, index_meta, market_data,
                         historical_price, predictions, signals, alerts, news,
                         transactions, paper_positions, paper_trades, market_reports
  data/
    catalog.py           Master list of NSE/BSE stocks + indices (sources of truth)
    master_stocks.json   Curated Indian equities (name, symbol, sector, cap)
    demo_data.py         Deterministic synthetic market generator
    providers.py         Demo + real provider adapters (Twelve Data, Alpha Vantage)
  analysis/
    indicators.py        MA/EMA/RSI/MACD/Bollinger/volatility/support-resistance
    time_series.py       5Y history fetch+cache, trend report
  predictions/
    engine.py            OLS trend + momentum + reversion + sklearn LinearRegression
                         ensemble, intervals, probabilities, backtesting (accuracy)
  ai/
    ollama_client.py     Local Ollama client (availability check + generate)
    ai_service.py        Stock analysis + market summary (rules fallback)
    rules_engine.py      Deterministic rule engine (always available)
  news/                  RSS fetching, sentiment, demo news, NewsService
  signals/               BUY/SELL/HOLD/WAIT engine + top-signals
  portfolio/             Manual portfolio tracking, FIFO sells, metrics
  paper/                 Simulated trading (virtual wallet)
  alerts/                Alert CRUD + evaluation + notifications
  reports/               Hourly/daily AI market reports
  services/              Dashboard composer, WebSocket feed builder
  routes/                FastAPI routers (stocks, analysis, predictions, news,
                         signals, portfolio, paper, alerts, reports, dashboard, ws)
  scheduler.py           Every 60 s: refresh market data + indices; generate
                         hourly reports in market hours; validate predictions.
```

## 3. Phases (as specified)

1. ✅ Project setup, frontend, dashboard
2. ✅ Indian stock market data integration (demo + provider adapters)
3. ✅ Five-year historical analysis + interactive charts (1D..5Y + compare)
4. ✅ Technical indicators & analysis (RSI, MACD, BB, volatility, SR, drawdown)
5. ✅ Ollama AI integration (rule engine fallback, no invented numbers)
6. ✅ Financial news aggregation + sentiment (RSS, sentiment scoring, dedupe)
7. ✅ Predictive modelling + accuracy tracking (ensemble + intervals + backtest)
8. ✅ BUY/SELL/HOLD decision-support engine
9. ✅ Portfolio management + paper trading (₹1,00,000 initial)
10. ✅ Alerts, reports, testing, deployment
11. ✅ Live dashboard + WebSocket feed (60 s)

## 4. Getting Started

### 4.1 Backend (FastAPI)

```powershell
# From the repo root
cd backend
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

Configure optional credentials via environment variables (see §5).

Run:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API base URL: `http://127.0.0.1:8000`. Health check: `GET /api/health`.

### 4.2 Frontend (Next.js)

```powershell
cd frontend
npm install
npm run dev    # http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` to the backend URL for production deploys.

### 4.3 Database setup (PostgreSQL recommended; SQLite is the dev default)

`backend/app/config.py` reads `DATABASE_URL`; if unset it uses a local SQLite file at `backend\data\app.db`. For PostgreSQL, create a database and set:

```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/indianstocks
```

Then `POST /api/...`? No — DB is created/migrated via `Base.metadata.create_all` on startup (see `database.init_db`), called from the app lifespan.

### 4.4 Ollama setup (optional, local AI)

```
ollama pull llama3.1:8b
```

Set `OLLAMA_URL=http://localhost:11434`, `OLLAMA_MODEL=llama3.1:8b`. The platform checks `GET /api/tags`; when unreachable, all AI features degrade to the deterministic rule engine (never silent failure of analysis — the rule engine is always available).

## 5. Configuration (.env, optional)

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://...` or `sqlite:///path` |
| `TWELVE_DATA_API_KEY` | Twelve Data EOD/quote API key (optional) |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key (optional) |
| `OLLAMA_URL` | Ollama server URL (default `http://localhost:11434`) |
| `OLLAMA_MODEL` | Ollama model name (default `llama3.1:8b`) |
| `PAPER_TRADING_INITIAL_BALANCE` | Virtual wallet (default `100000`) |
| `NEXT_PUBLIC_API_URL` | Frontend → backend base URL |

## 6. API Reference (highlights)

- `GET /api/health` — service status, data sources, demo flag
- `GET /api/stocks?limit=` — all tracked equities with live quotes
- `GET /api/stocks/{symbol}` — meta, quote, 5Y history, technical analysis
- `GET /api/search?q=` — symbol/name/sector search
- `GET /api/indices`, `GET /api/indices/{symbol}/history`
- `GET /api/analysis/{symbol}` — AI commentary + technicals
- `GET/POST /api/predictions/...` — forecasts (15 min … 5 days), accuracy
- `GET /api/news`, `/api/news/symbol/{s}`, `/api/news/sector/{s}`
- `GET/POST /api/signals`, `/api/signals/{s}`, `/api/signals/generate/{s}`
- `POST /api/portfolio/transaction`, `GET /api/portfolio/summary`
- `POST/GET /api/paper/order`, `GET /api/paper/wallet`, `/api/paper/trades`
- `POST /api/alerts`, `GET /api/alerts`, `GET /api/alerts/notifications`, `POST /api/alerts/evaluate`
- `POST /api/reports/hourly|daily`, `GET /api/reports`
- `GET /api/dashboard` — composed terminal-style dashboard
- `WS /api/ws/market-updates` — live market updates every 60 s

## 7. Testing

```powershell
& python backend\tests\smoke_tests.py    # indicators, signals, predictions, paper, alerts, news
& python backend\tests\api_smoke.py      # API endpoints against a running backend
```

## 8. Deployment notes

- Frontend: Vercel (`npm run build`).
- Backend: any WSGI/ASGI host (uvicorn, Gunicorn+uvicorn workers). Keep the WebSocket endpoint reachable.
- Data-licensing: Alpha Vantage and Twelve Data data is used per their terms; demo mode is labelled.

## 9. Notes on Data Accuracy

- Every metric is tagged with `source` (e.g., `demo`, `alpha-vantage`, `twelve-data`), `is_live`, and `delay_minutes` where applicable.
- The LLM is never used to invent numbers: prompts instruct it to explain only verified data; JSON parsing failures fall back to the rule engine.
- Historical prices come from the provider adapter or demo generator; nothing is hardcoded.

---

Happy trading, carefully.
