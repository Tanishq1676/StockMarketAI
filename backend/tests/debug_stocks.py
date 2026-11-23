"""Debug the SSR 500s: fetch /api/stocks/{symbol} and /api/stocks directly."""

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def get(p):
    try:
        with urllib.request.urlopen(BASE + p, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return "ERR", repr(e)[:80]


def main():
    for sym in ["BANKNIFTY", "SENSEX", "NIFTY500"]:
        s, d = get(f"/api/stocks/{sym}")
        print(f"/api/stocks/{sym} -> {s}")
        if s != 200:
            print("   body:", str(d)[:250])
    s, d = get("/api/stocks?limit=2")
    if isinstance(d, dict):
        print("/api/stocks ->", s, "first symbols:", [x["symbol"] for x in d["stocks"][:5]])
    else:
        print("/api/stocks ->", s, str(d)[:150])
    s, d = get("/api/indices")
    idx = d.get("indices", []) if isinstance(d, dict) else []
    print("/api/indices ->", s, "count:", len(idx))
    if idx:
        print("   first:", idx[0])
    names = sorted({i.get("symbol") for i in idx})
    print("   symbols:", names)


if __name__ == "__main__":
    main()
