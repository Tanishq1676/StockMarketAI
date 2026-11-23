# Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ Frontend (Next.js, React, TypeScript, Tailwind)                     │
│   Dashboard · Stocks · Stock detail · Portfolio · Paper trading     │
│   Alerts · News · Search bar · Charts (lightweight-charts)          │
└───────────────────────┬─────────────────────────────────────────────┘
                        │ HTTPS (REST / JSON) + WebSocket (60s updates)
┌───────────────────────▼─────────────────────────────────────────────┐
│ Backend (FastAPI + SQLAlchemy, PostgreSQL/SQLite)                   │
│                                                                      │
│  Providers   analysis     predictions     ai         news          │
│  data/       analysis/    predictions/    ai/        news/          │
│  catalog     indicators,  engine,         ai_service sources,        │
│  providers   time_series  rules_engine     ollama     services,      │
│  demo_data                                            reports        │
│                                                                      │
│  Services/Reports/Alerts/PaperTrading/Portfolio/Signals/Dashboard   │
│  scheduler.py  (APScheduler: refresh 60s, hourly reports in hours)  │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────────┐
│ External (optional, verified, per-licensing)                        │
│  Twelve Data API, Alpha Vantage API, RSS feeds (ET/Moneycontrol/…)  │
│  Ollama (local, e.g. llama3.1:8b)                                   │
│  PostgreSQL                                                         │
└─────────────────────────────────────────────────────────────────────┘
```

## Data flow

1. **On startup** — DB init + catalog seeding (stocks + indices).
2. **Every 60 s** — scheduler refreshes quotes for stocks + indices; stores into `market_data` with `data_source`/`is_live`/`delay_minutes` provenance.
3. **On demand** — `/api/stocks/{s}` → provider quote + cached 5Y history → technical analysis (`time_series_report`), AI summary, predictions, signals, news.
4. **Hourly (market hours)** — AI market report (`/api/reports/hourly`).

## Key invariants

- All numbers are produced by pandas/numpy/sklearn/indicator code over stored data; LLM text is explanation only (never invent numbers).
- Signals carry entry/target/stop-loss/risk-reward/confidence — predictions carry intervals + probabilities.
- Paper trading never touches real exchanges; portfolio records require explicit user action.
- Alerts evaluate on stored market data; fired alerts become notifications.
