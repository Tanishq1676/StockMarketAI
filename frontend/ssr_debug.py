"""Debug SSR on port 3000: fetch /stocks/TATAMOTORS and print status/body snippet."""

import urllib.error
import urllib.request


def get(p):
    try:
        with urllib.request.urlopen("http://127.0.0.1:3000" + p, timeout=90) as r:
            return r.status, r.read().decode()[:1500]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:1500]
    except Exception as e:
        return "ERR", repr(e)[:100]


def main():
    for p in ["/", "/stocks/TATAMOTORS", "/stocks/BANKNIFTY"]:
        s, t = get(p)
        print(f"== {p} -> {s}")
        if s != 200:
            print(t[:400])


if __name__ == "__main__":
    main()
