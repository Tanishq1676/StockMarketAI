"""Check /api/analysis sentiment_score presence across many symbols."""

import json
import urllib.error
import urllib.request

SYMS = ["TATAMOTORS", "INFY", "RELIANCE", "BANKNIFTY", "TCS", "SENSEX", "NIFTY500", "BAJAJFINSV", "HDFCBANK", "MARUTI", "APPLE", "SENSEX"]


def main():
    for s in SYMS:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:8000/api/analysis/{s}", timeout=60) as r:
                d = json.loads(r.read().decode())
            v = d.get("sentiment_score", "MISSING")
            rsi = d.get("rsi14_last")
            news = len(d.get("news", []))
            print(f"{s}: status=200 sentiment_score={v!r} rsi={rsi!r} news={news}")
        except urllib.error.HTTPError as e:
            print(f"{s}: status={e.code}")
        except Exception as e:
            print(f"{s}: ERR {repr(e)[:70]}")


if __name__ == "__main__":
    main()
