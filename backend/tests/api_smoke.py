"""API smoke test against a running backend on 127.0.0.1:8000."""

import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"


def get(p):
    try:
        with urllib.request.urlopen(BASE + p, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def main():
    checks = [
        "/api/health",
        "/api/stocks?limit=5",
        "/api/indices",
        "/api/search?q=tcs&limit=5",
        "/api/signals?n=3",
        "/api/news?limit=5",
        "/api/paper/wallet",
        "/api/portfolio/summary",
        "/api/predictions/accuracy",
    ]
    for p in checks:
        s, d = get(p)
        extra = ""
        if isinstance(d, dict):
            if p == "/api/health":
                extra = " " + json.dumps(d)[:200]
            elif p == "/api/stocks?limit=5" and d.get("stocks"):
                extra = f" first={d['stocks'][0]['symbol']} src={d['stocks'][0]['data_source']}"
            elif p == "/api/indices":
                extra = f" count={len(d.get('indices', []))}"
        print(p, "->", s, extra)

    # detail endpoints
    for p in ["/api/stocks/TATAMOTORS", "/api/analysis/TATAMOTORS"]:
        s, d = get(p)
        if isinstance(d, dict):
            print(p, "->", s, "close:", (d.get("quote") or {}).get("close"),
                  "src:", d.get("data_source") or d.get("quote", {}).get("data_source"))
        else:
            print(p, "->", s, str(d)[:200])


if __name__ == "__main__":
    main()
