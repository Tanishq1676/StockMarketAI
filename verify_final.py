"""Final verification after the StockDetailView fixes."""

import json
import os
import re
import urllib.error
import urllib.request

BACKEND = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:3000"
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
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name + (" | " + detail if detail else ""))
        ok = ok and bool(cond)

    s, d = get(BACKEND, "/api/health")
    check("backend /api/health", s == 200, f"status={s}")

    # /api/stocks/{symbol} for all key symbols (stocks + indices)
    for sym in ["TATAMOTORS", "BANKNIFTY", "SENSEX", "NIFTY500"]:
        s, d = get(BACKEND, f"/api/stocks/{sym}")
        check(f"backend /api/stocks/{sym}", s == 200, f"status={s}")
    s, d = get(BACKEND, "/api/stocks/TATAMOTORS")
    check("analysis.sentiment_score present (stocks)", isinstance(d, str) and '"sentiment_score"' in d,
          f"status={s} sentiment={json.loads(d)['analysis'].get('sentiment_score') if s == 200 and d else ''}")
    s, d = get(BACKEND, "/api/analysis/TATAMOTORS")
    v = json.loads(d).get("sentiment_score") if s == 200 else None
    check("analysis/TATAMOTORS sentiment_score is number", isinstance(v, (int, float)), f"value={v!r}")

    s, d = get(BACKEND, "/api/signals/generate/TATAMOTORS", "POST")
    check("backend POST /api/signals/generate", s == 200, f"status={s}")
    s, d = get(BACKEND, "/api/predictions/generate/TATAMOTORS", "POST")
    check("backend POST /api/predictions/generate", s == 200, f"status={s}")
    s, d = get(BACKEND, "/api/reports/hourly", "POST")
    check("backend POST /api/reports/hourly", s == 200, f"status={s}")

    # SSR checks
    for sym in SYMS:
        s, html = get(FRONTEND, f"/stocks/{sym}")
        crashed = "Internal error" in html or "Type error" in html
        check(f"SSR /stocks/{sym}", s == 200 and not crashed, f"status={s}")
    s, html = get(FRONTEND, "/stocks/TATAMOTORS")
    check("SSR shows Sentiment line (user's bug fixed)", "Sentiment" in html, f"status={s}")
    s, html = get(FRONTEND, "/")
    check("SSR / dashboard", s == 200 and "Dashboard" in html, f"status={s}")

    print("OVERALL:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
