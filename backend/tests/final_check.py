"""Final end-to-end verification of the platform.

Checks:
1. Backend health + key endpoints.
2. Frontend dev server: port + all pages return 200.
"""

import json
import re
import time
import urllib.request
import urllib.error


def backend_get(p, method="GET", timeout=60):
    req = urllib.request.Request("http://127.0.0.1:8000" + p, method=method,
                                 data=b"{}" if method == "POST" else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:
        return "ERR", repr(e)[:80]


def frontend_get(p, timeout=90):
    try:
        with urllib.request.urlopen("http://127.0.0.1:3000" + p, timeout=timeout) as r:
            return r.status, r.read().decode()
    except Exception as e:
        return "ERR", repr(e)[:80]


def main():
    results = []
    # wait for frontend up
    for _ in range(30):
        s, _ = frontend_get("/", timeout=5)
        if s == 200:
            break
        time.sleep(2)

    print("== Backend ==")
    s, d = backend_get("/api/health")
    print("health:", s, d)
    s, d = backend_get("/api/indices")
    print("indices:", s, len(d.get("indices", [])))
    s, d = backend_get("/api/stocks?limit=5")
    print("stocks:", s, (d.get("stocks") or [{}])[0].get("symbol") if isinstance(d, dict) else d)
    s, d = backend_get("/api/signals/generate/TATAMOTORS", method="POST")
    print("signals/generate:", s, (d.get("signal") or {}).get("signal_type") if isinstance(d, dict) else d)
    s, d = backend_get("/api/predictions/generate/TATAMOTORS", method="POST")
    print("predictions/generate:", s, len(d.get("forecasts", [])) if isinstance(d, dict) else d)
    s, d = backend_get("/api/reports/hourly", method="POST")
    print("reports/hourly:", s, (d.get("report_type") if isinstance(d, dict) else d))

    print("== Frontend ==")
    for p in ["/", "/stocks", "/stocks/TATAMOTORS", "/portfolio", "/paper-trading", "/alerts", "/news", "/reports"]:
        s, t = frontend_get(p)
        has_err = "Internal error" in t or "Type error" in t
        m = re.search(r"<title>([^<]*)</title>", t)
        results.append((p, s, has_err))
        print(p, "->", s, ("ERR!" if has_err else ""), (m.group(1)[:36] if m else ""))

    bad = [r for r in results if r[1] != 200 or r[2]]
    print("VERDICT:", "ALL PASS" if not bad else f"FAILURES: {bad}")


def _backend_get(p, method="GET"):
    return backend_get(p)


if __name__ == "__main__":
    main()
