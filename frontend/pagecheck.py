"""Fetch key pages of the dev frontend and report status + errors."""

import json
import re
import urllib.request

BASE = "http://127.0.0.1:3000"


def get(p):
    try:
        with urllib.request.urlopen(BASE + p, timeout=90) as r:
            return r.status, r.read().decode()
    except Exception as e:
        return "ERR", repr(e)[:80]


def main():
    out = []
    for p in ["/", "/stocks", "/stocks/TATAMOTORS", "/portfolio", "/paper-trading", "/alerts", "/news", "/reports"]:
        s, t = get(p)
        m = re.search(r"<title>([^<]*)</title>", t)
        has_err = "Internal error" in t or "Type error" in t
        out.append(f"{p} -> {s}{' ERR!' if has_err else ''} {m.group(1)[:36] if m else ''}")
    with open("pagecheck.json", "w") as f:
        json.dump(out, f, indent=1)
    print("WROTE pagecheck.json")


if __name__ == "__main__":
    main()
