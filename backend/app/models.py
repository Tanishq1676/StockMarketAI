"""Database models for the Indian Stock Market Intelligence Platform.

Every market number carries provenance fields (`source`, `is_live`,
`delay_minutes`) so the UI can clearly distinguish live, delayed and
historical data, as required by the data-accuracy policy.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer, JSON,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class StockMeta(Base):
    """Metadata for a listed stock (NSE and/or BSE)."""

    __tablename__ = "stock_meta"
    __table_args__ = (UniqueConstraint("symbol", "exchange"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)  # canonical NSE symbol
    bse_symbol: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    isin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bse_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)  # NSE or BSE
    sector: Mapped[str] = mapped_column(String(60), default="")
    market_cap: Mapped[str] = mapped_column(String(20), default="")  # small/mid/large
    nse_indices: Mapped[List[str]] = mapped_column(JSON, default=list)
    data_source: Mapped[str] = mapped_column(String(40), default="demo")
    status: Mapped[str] = mapped_column(String(20), default="active")

    def __repr__(self):
        return f"<StockMeta {self.exchange}:{self.symbol}>"


class IndexMeta(Base):
    """Indices: NIFTY50, BANK NIFTY, sectoral indices, NIFTY 100/500, etc."""

    __tablename__ = "index_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # market_index, sectoral, custom
    exchange: Mapped[str] = mapped_column(String(10), default="NSE")
    data_source: Mapped[str] = mapped_column(String(40), default="demo")

    def __repr__(self):
        return f"<IndexMeta {self.symbol}>"


class MarketData(Base):
    """Latest verified quote for a symbol."""

    __tablename__ = "market_data"
    __table_args__ = (UniqueConstraint("symbol", "data_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    price_open: Mapped[float] = mapped_column(Float)
    price_high: Mapped[float] = mapped_column(Float)
    price_low: Mapped[float] = mapped_column(Float)
    price_close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(Integer)
    change_pct: Mapped[float] = mapped_column(Float)  # always percent, never a fraction
    prev_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)  # ingest time (UTC)
    trade_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # actual session YYYY-MM-DD
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    data_source: Mapped[str] = mapped_column(String(40))
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    delay_minutes: Mapped[int] = mapped_column(Integer, default=0)


class HistoricalPrice(Base):
    """OHLCV daily history for stocks and indices."""

    __tablename__ = "historical_price"
    __table_args__ = (UniqueConstraint("symbol", "date", "source", "exchange"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    pct_change: Mapped[float] = mapped_column(Float, default=0.0)
    prev_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="demo")
    exchange: Mapped[str] = mapped_column(String(10), default="NSE")
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class IndexHistory(Base):
    """OHLCV daily history for indices."""

    __tablename__ = "index_history"
    __table_args__ = (UniqueConstraint("symbol", "date", "source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[str] = mapped_column(String(10), nullable=False)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    pct_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="demo")
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Prediction(Base):
    """ML/statistical price predictions and their future validation."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    horizon_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_close: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # up/down/flat
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_type: Mapped[str] = mapped_column(String(40), nullable=False)
    features: Mapped[List[float]] = mapped_column(JSON, default=list)
    price_anchor: Mapped[float] = mapped_column(Float, nullable=False)  # price used as model input
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    actual_close: Mapped[float] = mapped_column(Float, default=0.0)
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    error_pct: Mapped[float] = mapped_column(Float, default=0.0)
    direction_correct: Mapped[Optional[bool]] = mapped_column(Boolean, default=None, nullable=True)


class Signal(Base):
    """AI/rule based BUY / SELL / HOLD / WAIT_FOR_CONFIRMATION signals."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(24), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasons: Mapped[List[str]] = mapped_column(JSON, default=list)
    entry_price: Mapped[float] = mapped_column(Float)
    target_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    risk_reward: Mapped[float] = mapped_column(Float)
    expected_holding_minutes: Mapped[int] = mapped_column(Integer, default=0)
    tech_reasons: Mapped[List[str]] = mapped_column(JSON, default=list)
    fund_reasons: Mapped[List[str]] = mapped_column(JSON, default=list)
    news_sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(12), default="medium")
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    ai_source: Mapped[str] = mapped_column(String(40), default="rule_engine")


class NewsArticle(Base):
    """Affected-company news with sentiment analysis, deduped by link."""

    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    link: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    symbol: Mapped[str] = mapped_column(String(20), default="")
    sector: Mapped[str] = mapped_column(String(60), default="")
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)  # -1.0..1.0
    impact: Mapped[str] = mapped_column(String(12), default="neutral")  # positive/negative/neutral
    analysis_source: Mapped[str] = mapped_column(String(40), default="demo")


class Transaction(Base):
    """Manual portfolio transactions (buy/sell) entered by the user."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(8), nullable=False)  # buy / sell
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    taxes: Mapped[float] = mapped_column(Float, default=0.0)
    other_fees: Mapped[float] = mapped_column(Float, default=0.0)
    date: Mapped[str] = mapped_column(String(10), default=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class PaperPosition(Base):
    """Open paper-trading position."""

    __tablename__ = "paper_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_entry: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class PaperTrade(Base):
    """Completed paper-trading order."""

    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class User(Base):
    """Basic user for alerts."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)


class Alert(Base):
    """Configured alerts + notification history."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    condition: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. price_above, pct_up, volume_spike
    threshold: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active / fired / dismissed
    fired_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class MarketReport(Base):
    """AI-generated hourly / daily market intelligence reports."""

    __tablename__ = "market_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)  # hourly / daily
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    data_source: Mapped[str] = mapped_column(String(40), default="demo")


class ServerSetting(Base):
    """Runtime key-value settings stored in the DB."""

    __tablename__ = "server_settings"
    __table_args__ = (UniqueConstraint("key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(200), nullable=False)


class IngestRun(Base):
    """Audit trail for every market-data ingestion run."""

    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job: Mapped[str] = mapped_column(String(60), nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="nse")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running/completed/failed
    rows_fetched: Mapped[int] = mapped_column(Integer, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    latest_trade_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
