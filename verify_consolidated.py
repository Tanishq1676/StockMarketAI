"""One-shot consolidated verification for the Stock Detail page + key endpoints."""

import json
import urllib.error
import urllib.request

B = "http://127.0.0.1:8000"
F = "http://127.0.0.1:3000"
SYMS = ["TATAMOTORS", "INFY", "RELIANCE", "BANKNIFTY", "TCS", "SENSEX", "NIFTY500", "BAJAJFINSV", "HDFCBANK"]


def get(base, p, method="GET", body=None):
    req = urllib.request.Request(base + p, method=method,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:
        return "ERR", repr(e)[:80]


def main():
    s, d = get(B, "/api/health")
    print("backend /api/health:", s, (json.loads(d)["status"] if s == 200 else d)[:60])
    s, d = get(B, "/api/indices")
    idx = json.loads(d).get("indices", []) if s == 200 and isinstance(d, str) else []
    print(f"backend /api/indices: {s} (count={len(idx)})")
    for sym in ["BANKNIFTY", "SENSEX", "NIFTY500", "BAJAJFINSV", "HDFCBANK", "TATAMOTORS"]:
        s, d = get(B, f"/api/stocks/{sym}")
        print(f"backend /api/stocks/{sym}: {s}")
    for p, m in [("/api/signals/generate/TATAMOTORS", "POST"), ("/api/predictions/generate/TATAMOTORS", "POST"), ("/api/reports/hourly", "POST")]:
        s, d = get(B, p, m)
        print(f"backend {m} {p}: {s}")
    for sym in SYMS:
        s, html = get(F, f"/stocks/{sym}")
        crashed = "Internal error" in html or "Type error" in html
        print(f"SSR /stocks/{sym}: {s} {'CRASH!' if crashed else ''}")
    s, html = get(F, "/")
    print("SSR /:", s)
    s, html = get(F, "/stocks/TATAMOTORS")
    print("SSR shows 'Sentiment' line:", "Sentiment" in (html or ""))


if __name__ == "__main__":
    main()
