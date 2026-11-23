"""News sentiment analysis: deterministic keyword scoring.

Score range: -1.0 (very negative) .. +1.0 (very positive). 0.0 = neutral.
"""

from __future__ import annotations

import re
from typing import List

NEGATIVE_WORDS = {
    "crash", "fall", "down", "slide", "drop", "decline", "cut", "lower", "plummet",
    "selloff", "sell-off", "bearish", "negative", "weak", "weakness", "dip",
    "recession", "fear", "panic", "concern", "downgrade", "scam", "fraud",
    "correction", "tumble", "slump", "sharp", "danger", "risk", "hit",
    "sanction", "probe", "investigation", "default", "misses", "breach",
}
POSITIVE_WORDS = {
    "rise", "rises", "up", "rally", "jump", "gain", "gains", "surge", "soar",
    "bullish", "positive", "strength", "strength", "win", "support", "strong",
    "boom", "bounce", "optimism", "approval", "boost", "upgrade", "record",
    "top", "better", "growth", "opportunity", "bonus", "haven", "vote",
    "beats", "target", "exceeds", "recovery", "extended", "expansion", "surge",
    "success", "heal", "heated", "vision",
}
NEGATIVE_STRONG = {"crash", "selloff", "sell-off", "plummet", "panic", "recession", "downgrade"}


def normalise(text: str) -> List[str]:
    return re.sub(r"[^a-z0-9\s]", " ", str(text).lower()).split()


def score_text(text: str) -> float:
    words = normalise(text)
    n = len(words)
    if not n:
        return 0.0
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    # strong negative words get extra weight
    pos_w = sum(1.6 for w in words if w in NEGATIVE_STRONG)
    neg_w = sum(1.6 for w in words if w in POSITIVE_WORDS)
    score = (pos + neg_w) - (neg + pos_w)
    # intensity-scaled, e.g. one strong negative word: -1.6/n... but clamp
    return max(-1.0, min(1.0, score / max(n, 1) * 4))


def classify_impact(score: float) -> str:
    if score > 0.3:
        return "positive"
    if score < -0.3:
        return "negative"
    return "neutral"
