"""Demo news generator: deterministic, labelled synthetic financial news.

Used only when no real news provider is reachable. Articles carry
`source="demo"` so the UI never pretends otherwise.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from typing import Dict, List

from ..data import catalog


def _seed(seed_text: str) -> int:
    return int(hashlib.md5(seed_text.encode()).hexdigest(), 16) % (2**31 - 1)


_TITLES_POSITIVE = [
    "Strong quarterly results beat analyst expectations",
    "Company announces record sales in Q{q}",
    "New contract wins worth %sINR million",
    "Dividend payout raised; investor confidence grows",
    "Stake sale leads to significant premium",
    "Company to expand production capacity",
    "Stock upgraded by research firms",
]

_TITLES_NEGATIVE = [
    "Quarterly profit misses estimates",
    "Company files for rights issue; shares rule lower",
    "Management change ahead of year end",
    "Regulatory probe deepens concerns",
    "Export volumes drop sharply",
    "Production halted due to snag",
]

_TITLES_NEUTRAL = [
    "Company announces strategic review",
    "Index provider updates constituents",
    "Board meeting scheduled",
    "Company lists new board members",
    "New product line extension announced",
]


def generate_demo_news(symbol: str, sector: str, count: int = 4, as_of: date = None) -> List[Dict]:
    seed = _seed(symbol + sector + (as_of.isoformat() if as_of else ""))
    rng = __import__("random").Random(seed)
    out = []
    for i in range(count):
        kind = rng.random()
        if kind < 0.4:
            title = rng.choice(_TITLES_POSITIVE)
        elif kind < 0.7:
            title = rng.choice(_TITLES_NEGATIVE)
        else:
            title = rng.choice(_TITLES_NEUTRAL)
        title = title.replace("%sINR million", f"{rng.randint(50, 400)}cr")
        pub = (as_of or date.today()) - timedelta(days=rng.randint(0, 3))
        out.append(
            {
                "title": f"[Demo] {symbol}: {title}",
                "source": "Economic Times (demo)",
                "link": f"https://demo.local/{symbol}/{pub.isoformat()}-{i}",
                "summary": f"Synthetic demonstration article for {symbol} in the {sector} sector. "
                           f"Demo mode is enabled; real market news requires credentials.",
                "published_at": datetime.combine(pub, datetime.min.time()).isoformat(),
                "symbol": symbol,
                "sector": sector,
                "sentiment_score": 0.2 if "positive" in title.lower() or "beat" in title.lower() else (-0.2 if "miss" in title.lower() or "drop" in title.lower() else 0.0),
                "impact": "positive" if "beat" in title.lower() or "premium" in title.lower() else ("negative" if "miss" in title.lower() or "rule lower" in title.lower() else "neutral"),
                "analysis_source": "demo",
            }
        )
    return out


def generate_market_headline(sector: str = "") -> Dict:
    """A generic market-direction headline (for dashboard summary)."""
    rng = __import__("random").Random(_seed("market-headline" + str(datetime.utcnow().date())))
    return {
        "title": f"[Demo] Indian equity markets trade in a mixed session" + (f" - {sector} sector update" if sector else ""),
        "source": "Market Monitor (demo)",
        "link": "https://demo.local/market",
        "summary": "Demo market summary for the dashboard; enable a news provider for live headlines.",
        "published_at": datetime.utcnow().isoformat(),
        "symbol": "",
        "sector": sector,
        "sentiment_score": 0.0,
        "impact": "neutral",
        "analysis_source": "demo",
    }
