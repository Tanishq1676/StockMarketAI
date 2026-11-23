"""SSR check for the Stock Detail page across multiple symbols."""

import re
import urllib.request
import urllib.error

SYMBOLS = ["TATAMOTORS", "INFY", "RELIANCE", "BANKNIFTY", "TCS", "SENSEX", "NIFTY500", "BAJAJFINSV", "HDFCBANK"]


def main():
    bad = []
    for sym in SYMBOLS:
        url = f"http://127.0.0.1:3000/stocks/{sym}"
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                html = r.read().decode()
            status = r.status
        except urllib.error.HTTPError as e:
            html = e.read().decode()
            status = e.code
        except Exception as e:
            print(f"{sym}: CONNECT ERROR {repr(e)[:80]}")
            bad.append(sym)
            continue
        crashed = "Internal error" in html or "Type error" in html
        m = re.search(r"<title>([^<]*)</title>", html)
        print(f"{sym}: status={status} crashed={crashed} title={m.group(1)[:30] if m else '-'}")
        if crashed or status != 200:
            bad.append(sym)
    print("RESULT:", "ALL OK" if not bad else f"PROBLEMS: {bad}")


if __name__ == "__main__":
    main()
