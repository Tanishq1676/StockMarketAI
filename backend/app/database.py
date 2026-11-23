"""Database setup.

Uses SQLAlchemy. Default dialect is PostgreSQL (as recommended in README);
when DATABASE_URL points to SQLite the app is fully functional as well.
"""

from __future__ import annotations

import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import DATABASE_URL

logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yield a DB session and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Columns added after the first release.  `create_all` cannot alter existing
# tables, so these are applied as additive migrations.  Nothing is dropped and
# no existing value is rewritten.
_ADDITIVE_COLUMNS = {
    "stock_meta": {
        "isin": "VARCHAR(20)",
        "bse_code": "VARCHAR(20)",
    },
    "market_data": {
        "prev_close": "FLOAT",
        "trade_date": "VARCHAR(10)",
        "fetched_at": "DATETIME",
        "source_url": "VARCHAR(300)",
    },
    "historical_price": {
        "prev_close": "FLOAT",
        "fetched_at": "DATETIME",
    },
    "index_history": {
        "pct_change": "FLOAT",
        "fetched_at": "DATETIME",
    },
}


def _apply_additive_migrations() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _ADDITIVE_COLUMNS.items():
            if table not in existing_tables:
                continue
            present = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name in present:
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                logger.info("added column %s.%s", table, name)

        # Index history predates its unique key.  Remove exact duplicates
        # (keeping the oldest row) before enforcing uniqueness.
        if "index_history" in existing_tables:
            conn.execute(
                text(
                    "DELETE FROM index_history WHERE id NOT IN ("
                    "SELECT MIN(id) FROM index_history GROUP BY symbol, date, source)"
                )
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_index_history_symbol_date_source "
                    "ON index_history (symbol, date, source)"
                )
            )
        # Query indexes for the hot read paths.
        for statement in (
            "CREATE INDEX IF NOT EXISTS ix_historical_symbol_date ON historical_price (symbol, date)",
            "CREATE INDEX IF NOT EXISTS ix_market_data_trade_date ON market_data (trade_date)",
            "CREATE INDEX IF NOT EXISTS ix_ingest_runs_started ON ingest_runs (started_at)",
        ):
            try:
                conn.execute(text(statement))
            except Exception as exc:  # pragma: no cover - dialect differences
                logger.debug("index creation skipped (%s): %s", statement, exc)


def init_db() -> None:
    """Create all tables if they do not exist, then apply additive migrations."""
    from . import models  # noqa: F401  (register models on Base)

    Base.metadata.create_all(bind=engine)
    _apply_additive_migrations()
