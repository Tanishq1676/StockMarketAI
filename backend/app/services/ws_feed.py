"""Live market WebSocket feed (Phase 11).

Broadcasts market updates every 60 seconds to connected browsers:
latest index status, top gainers, losers, most active and unusual volume.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from ..reports.helpers import build_market_context

logger = logging.getLogger(__name__)

REFRESH_INTERVAL = 60


def build_update_payload() -> Dict[str, Any]:
    ctx = build_market_context()
    return {
        "type": "market_update",
        "timestamp": _iso(),
        "indices": [
            {
                "symbol": d["symbol"],
                "name": d.get("name"),
                "price": round(d["price"], 2),
                "change_pct": round(d["change_pct"], 3),
                "prev_close": d.get("prev_close"),
                "trade_date": d.get("trade_date"),
                "direction": "up" if d["change_pct"] > 0 else ("down" if d["change_pct"] < 0 else "flat"),
                "data_source": d["data_source"],
                "is_live": d.get("is_live", False),
                "last_updated": d["last_updated"],
            }
            for d in ctx["index_movements"]
        ],
        "top_gainers": ctx["top_performers"],
        "top_losers": ctx["top_losers"],
        "most_active": ctx["most_active"][:8],
        "unusual_volume": ctx["unusual_volume"][:8],
    }


def _iso():
    from datetime import datetime

    return datetime.utcnow().isoformat()
