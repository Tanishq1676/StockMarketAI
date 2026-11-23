"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatSessionShort } from "@/lib/market";

const STORAGE_KEY = "indstock.watchlist";
const DEFAULT_SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK", "INFY"];

const fmt = (v: any) =>
  typeof v === "number" ? v.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "—";

export default function Watchlist() {
  const [all, setAll] = useState<any[]>([]);
  const [quotes, setQuotes] = useState<Record<string, any>>({});
  const [symbols, setSymbols] = useState<string[]>(DEFAULT_SYMBOLS);
  const [query, setQuery] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          setSymbols(parsed.filter((x) => typeof x === "string").slice(0, 8));
        }
      }
    } catch {
      /* use defaults */
    }
    setReady(true);
  }, []);

  // Full catalogue is used only for add-symbol suggestions.
  useEffect(() => {
    let alive = true;
    api
      .get<any>("/api/stocks?limit=500")
      .then((d) => {
        if (alive) setAll(d.stocks || []);
      })
      .catch(() => {
        if (alive) setAll([]);
      });
    return () => {
      alive = false;
    };
  }, []);

  // Quote rows for the saved watchlist only, refreshed with the market snapshot.
  useEffect(() => {
    let alive = true;
    const load = () => {
      if (!symbols.length) {
        setQuotes({});
        return;
      }
      api
        .get<any>(`/api/stocks?symbols=${encodeURIComponent(symbols.join(","))}`)
        .then((d) => {
          if (!alive) return;
          const map: Record<string, any> = {};
          for (const row of d.stocks || []) map[row.symbol] = row;
          setQuotes(map);
        })
        .catch(() => {
          if (alive) setQuotes({});
        });
    };
    load();
    const t = setInterval(load, 60_000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [symbols]);

  const save = (next: string[]) => {
    setSymbols(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* storage may be unavailable */
    }
  };

  const add = (value: string) => {
    const symbol = value.trim().toUpperCase();
    if (!symbol || symbols.includes(symbol) || symbols.length >= 8) return;
    if (!all.some((s) => s.symbol === symbol)) return;
    save([...symbols, symbol]);
    setQuery("");
  };

  const remove = (symbol: string) => save(symbols.filter((s) => s !== symbol));

  const q = query.trim().toUpperCase();
  const suggestions = q
    ? all
        .filter(
          (s) =>
            !symbols.includes(s.symbol) &&
            (s.symbol.includes(q) || String(s.name || "").toUpperCase().includes(q))
        )
        .slice(0, 5)
    : [];

  const rows = symbols.map((symbol) => {
    const match = quotes[symbol] || all.find((s) => s.symbol === symbol);
    return (
      match || {
        symbol,
        name: "",
        price: null,
        change_pct: null,
      }
    );
  });

  return (
    <section className="glass-card card-hover flex flex-col p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="card-title">Watchlist</h2>
          <p className="card-sub">Your tracked symbols, stored locally</p>
        </div>
        <span className="pill pill-flat">{symbols.length}/8</span>
      </div>

      <form
        className="relative mt-4"
        onSubmit={(e) => {
          e.preventDefault();
          add(query);
        }}
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Add symbol…"
          aria-label="Add symbol to watchlist"
          className="field h-9 pr-10 text-xs"
        />
        <button
          type="submit"
          aria-label="Add symbol"
          disabled={!query.trim() || symbols.length >= 8}
          className="absolute right-1.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md bg-accent-soft text-accent-dark transition hover:bg-accent-dim disabled:opacity-40"
        >
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>

        {suggestions.length > 0 && (
          <div className="absolute inset-x-0 top-full z-30 mt-1.5 overflow-hidden rounded-xl border border-line/90 bg-white/95 py-1 shadow-xl backdrop-blur-xl">
            {suggestions.map((s) => (
              <button
                key={s.symbol}
                type="button"
                onClick={() => add(s.symbol)}
                className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left transition-colors hover:bg-accent-soft/80"
              >
                <span className="min-w-0">
                  <span className="block text-xs font-bold text-ink">{s.symbol}</span>
                  <span className="block truncate text-[10px] text-fg-muted">{s.name}</span>
                </span>
                <span className="text-[10px] font-semibold text-accent">Add</span>
              </button>
            ))}
          </div>
        )}
      </form>

      <div className="mt-3 flex-1">
        {!ready ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="skeleton h-12 rounded-xl" />
            ))}
          </div>
        ) : rows.length ? (
          <ul className="divide-y divide-line/60">
            {rows.map((s) => {
              const change = typeof s.change_pct === "number" ? s.change_pct : null;
              const up = change != null && change > 0;
              const down = change != null && change < 0;
              return (
                <li key={s.symbol} className="group flex items-center gap-2 py-2.5">
                  <Link href={`/stocks/${s.symbol}`} className="flex min-w-0 flex-1 items-center gap-2.5">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-line/80 bg-white text-[10px] font-extrabold text-accent-dark">
                      {s.symbol.slice(0, 3)}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-xs font-bold text-ink transition-colors group-hover:text-accent-dark">
                        {s.symbol}
                      </span>
                      <span className="num block text-[10px] text-fg-dim">
                        ₹{fmt(s.price)}
                        {s.trade_date ? ` · ${formatSessionShort(s.trade_date)}` : ""}
                      </span>
                    </span>
                  </Link>
                  <span className={`pill !px-2 !py-0.5 !text-[10px] ${up ? "pill-up" : down ? "pill-down" : "pill-flat"}`}>
                    {up ? "▲" : down ? "▼" : "•"}{" "}
                    {change != null ? `${change > 0 ? "+" : ""}${change.toFixed(2)}%` : "—"}
                  </span>
                  <button
                    type="button"
                    onClick={() => remove(s.symbol)}
                    aria-label={`Remove ${s.symbol} from watchlist`}
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-fg-dim opacity-0 transition hover:bg-down/10 hover:text-down group-hover:opacity-100"
                  >
                    <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round">
                      <path d="M6 6l12 12M18 6L6 18" />
                    </svg>
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <div className="rounded-xl border border-dashed border-line bg-white/40 px-3 py-8 text-center text-xs text-fg-muted">
            Add a symbol above to start your watchlist.
          </div>
        )}
      </div>

      <p className="mt-3 text-[10px] leading-relaxed text-fg-dim">
        Saved in this browser only. Prices refresh with the market snapshot.
      </p>
    </section>
  );
}
