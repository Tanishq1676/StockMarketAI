"""Final comprehensive verification: backend endpoints + SSR for multiple symbols."""

import json
import os
import re
import urllib.request
import urllib.error

USERPROFILE = os.environ.get("USERPROFILE", "")
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
        print(("PASS" if cond else "FAIL"), name, detail if not cond else "")
        ok = ok and bool(cond)

    s, d = get(BACKEND, "/api/health")
    check("backend /api/health", s == 200)
    idx = []
    for _ in range(30):
        s, d = get(BACKEND, "/api/indices")
        idx = d.get("indices", []) if isinstance(d, dict) else []
        if s == 200 and idx:
            break
        import time as _t
        _t.sleep(2)
    check("backend /api/indices", s == 200 and len(idx) > 0, f"status={s} count={len(idx)}")
    s, d = get(BACKEND, "/api/stocks?limit=5")
    check("backend /api/stocks", s == 200, f"status={s} body={str(d)[:100]}")
    s, d = get(BACKEND, "/api/signals/generate/TATAMOTORS", "POST")
    check("backend POST /api/signals/generate", s == 200, f"status={s} body={str(d)[:100]}")
    s, d = get(BACKEND, "/api/predictions/generate/TATAMOTORS", "POST")
    check("backend POST /api/predictions/generate", s == 200, f"status={s} body={str(d)[:100]}")
    s, d = get(BACKEND, "/api/reports/hourly", "POST")
    check("backend POST /api/reports/hourly", s == 200, f"status={s} body={str(d)[:100]}")

    # SSR checks: dev server must be up; the StockDetail page must not crash.
    for sym in SYMS:
        try:
            s, html = get(FRONTEND, f"/stocks/{sym}")
        except Exception:
            s, html = "ERR", ""
        crashed = ("Internal error" in html or "Type error" in html) if isinstance(html, str) else True
        check(f"SSR /stocks/{sym}", s == 200 and not crashed, f"status={s}")
    # The user's bug: 'Sentiment ... .toFixed' — confirm Sentiment line renders.
    try:
        s, html = get(FRONTEND, "/stocks/TATAMOTORS")
    except Exception:
        s, html = "ERR", ""
    check("SSR shows Sentiment line", isinstance(html, str) and "Sentiment" in html, f"status={s}")

    print("OVERALL:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
