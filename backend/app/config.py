"""Configuration for the Indian Stock Market Intelligence Platform.

All secrets live here and are read from environment variables. Nothing is
hardcoded. Demo mode is used when no real data provider credentials are
available; every market payload carries a `data_source` field so the UI can
show exactly where its numbers came from.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parent.parent  # .../backend
BASE_DIR = BACKEND_DIR.parent  # project root

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Default: PostgreSQL if configured, otherwise a local SQLite file. The
# platform is fully functional on SQLite; PostgreSQL is recommended for
# production and is the documented default in README.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    db_dir = BACKEND_DIR / "data"
    db_dir.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite:///{db_dir / 'app.db'}"

# ---------------------------------------------------------------------------
# Real data providers (optional)
# ---------------------------------------------------------------------------
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
TWELVE_DATA_BASE_URL = os.getenv("TWELVE_DATA_BASE_URL", "https://api.twelvedata.com").strip()
ALPHA_VANTAGE_BASE_URL = os.getenv("ALPHA_VANTAGE_BASE_URL", "https://www.alphavantage.co").strip()

# ---------------------------------------------------------------------------
# AI (Ollama, running locally)
# ---------------------------------------------------------------------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip()
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "15"))

# ---------------------------------------------------------------------------
# Paper trading defaults
# ---------------------------------------------------------------------------
PAPER_TRADING_INITIAL_BALANCE = float(os.getenv("PAPER_TRADING_INITIAL_BALANCE", "100000"))

# ---------------------------------------------------------------------------
# Demo mode flag (set by provider resolution; also exposed for the UI)
# ---------------------------------------------------------------------------
DEMO_MODE_DEFAULT = (not TWELVE_DATA_API_KEY) and (not ALPHA_VANTAGE_API_KEY)

# Indian market trading hours (IST): 9:15 AM - 3:30 PM, Monday-Friday.
MARKET_OPEN_MINUTES = 9 * 60 + 15
MARKET_CLOSE_MINUTES = 15 * 60 + 30
STOCK_MARKET_HOLIDAYS = []  # filled at runtime if a provider supplies them


class Settings(BaseModel):
    """Runtime settings that can also be stored/changed via /api/settings."""

    database_url: str = DATABASE_URL
    demo_mode: bool = DEMO_MODE_DEFAULT
    ollama_url: str = OLLAMA_URL
    ollama_model: str = OLLAMA_MODEL
    paper_trading_balance: float = PAPER_TRADING_INITIAL_BALANCE
    refresh_interval_seconds: int = 60
    ai_model_name_public: str = "local-ai-market-analyst"

    class Config:
        extra = "allow"


settings = Settings()


def list_sources() -> List[str]:
    sources: List[str] = []
    if TWELVE_DATA_API_KEY:
        sources.append("twelve-data")
    if ALPHA_VANTAGE_API_KEY:
        sources.append("alpha-vantage")
    sources.append("demo")
    return sources
