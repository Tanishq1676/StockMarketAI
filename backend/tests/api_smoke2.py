"""Functional endpoint test #2 (writes via POST paths)."""

import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"


def get(p):
    try:
        with urllib.request.urlopen(BASE + p, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def post(p):
    req = urllib.request.Request(BASE + p, data=b"{}", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def main():
    s, d = post("/api/predictions/generate/TATAMOTORS")
    print("POST predictions/generate/TATAMOTORS ->", s)
    if s == 200:
        for f in d["forecasts"][:6]:
            print("  ", f["horizon"], "pred", f["predicted_close"], "dir", f["direction"], "conf", f["confidence"], "bull", f["bullish_probability"], "bear", f["bearish_probability"])

    s, d = get("/api/predictions/TATAMOTORS")
    print("GET predictions/TATAMOTORS ->", s, "count:", len(d.get("predictions", [])))

    s, d = post("/api/signals/generate/TATAMOTORS")
    print("POST signals/generate/TATAMOTORS ->", s)
    if s == 200:
        sig = d["signal"]
        print("  ", sig["signal_type"], "conf", sig["confidence"], "entry", sig["entry_price"], "target", sig["target_price"], "sl", sig["stop_loss"], "r:r", sig["risk_reward"], "src", sig["ai_source"])
        print("   summary:", (sig.get("ai_summary") or "")[:120])

    s, d = get("/api/signals/TATAMOTORS")
    print("GET signals/TATAMOTORS ->", s, "signal:", d["signal"]["signal_type"] if d.get("signal") else None)

    s, d = get("/api/analysis/TATAMOTORS")
    print("GET analysis/TATAMOTORS ->", s)
    if isinstance(d, dict):
        print("   rsi:", d.get("rsi14_last"), "vol:", d.get("historical_volatility_annualized"), "ai_source:", d.get("ai_source"))
        print("   ai_summary:", (d.get("ai_summary") or "")[:150])

    s, d = get("/api/alerts/notifications")
    print("GET alerts/notifications ->", s, "n:", len(d.get("notifications", [])))


if __name__ == "__main__":
    main()
