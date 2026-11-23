"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

interface SearchResult {
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
  cap: string;
  indices: string[];
}

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    const t = setTimeout(async () => {
      if (!query.trim()) {
        setResults([]);
        return;
      }
      setLoading(true);
      try {
        const data = await api.get<{ results: SearchResult[] }>(
          `/api/search?q=${encodeURIComponent(query)}&limit=8`
        );
        setResults(data.results || []);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  const open = focused && query.trim().length > 0;

  return (
    <div className="relative w-full">
      <div className="relative">
        <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-fg-dim" aria-hidden>
          <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round">
            <circle cx="11" cy="11" r="7" />
            <path d="M16.5 16.5L21 21" />
          </svg>
        </span>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Search stocks, symbols or sectors…"
          aria-label="Search stocks"
          className="h-11 w-full rounded-xl border border-line bg-white/75 pl-10 pr-10 text-sm text-fg shadow-sm outline-none transition placeholder:text-fg-dim focus:border-accent/45 focus:bg-white"
          style={{ boxShadow: focused ? "0 0 0 4px rgba(14,138,95,0.10)" : undefined }}
        />
        {query ? (
          <button
            type="button"
            onClick={() => setQuery("")}
            aria-label="Clear search"
            className="absolute right-2.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-fg-dim transition hover:bg-surface-2 hover:text-ink"
          >
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        ) : (
          <span className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded-md border border-line/80 bg-surface-0 px-1.5 py-0.5 text-[10px] font-semibold text-fg-dim sm:block">
            NSE · BSE
          </span>
        )}
      </div>

      {open && (
        <div
          onMouseDown={(e) => e.preventDefault()}
          className="absolute inset-x-0 top-full z-50 mt-2 overflow-hidden rounded-2xl border border-line/90 bg-white/95 shadow-[0_24px_60px_-24px_rgba(9,56,38,0.45)] backdrop-blur-xl"
        >
          <div className="flex items-center justify-between border-b border-line/70 px-4 py-2.5">
            <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-fg-dim">
              Search results
            </span>
            {loading ? (
              <span className="text-[10px] font-medium text-accent">Searching…</span>
            ) : (
              <span className="text-[10px] font-medium text-fg-dim">{results.length} found</span>
            )}
          </div>

          {results.length > 0 ? (
            <ul className="max-h-[340px] overflow-y-auto py-1">
              {results.map((r) => (
                <li key={r.symbol}>
                  <Link
                    href={`/stocks/${r.symbol}`}
                    onClick={() => setQuery("")}
                    className="flex items-center gap-3 px-3 py-2.5 transition-colors hover:bg-accent-soft/80"
                  >
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line/80 bg-white text-[10px] font-extrabold text-accent-dark">
                      {r.symbol.slice(0, 3)}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-ink">{r.name}</span>
                      <span className="block truncate text-[11px] text-fg-muted">
                        {r.symbol} · {r.exchange} · {r.sector || r.cap || "Equity"}
                      </span>
                    </span>
                    <span className="shrink-0 text-[10px] font-medium text-fg-dim">
                      {(r.indices || []).slice(0, 2).join(" · ")}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-4 py-8 text-center">
              <p className="text-sm font-semibold text-fg">
                {loading ? "Searching the universe…" : "No matching equities"}
              </p>
              <p className="mt-1 text-xs text-fg-muted">
                Try a symbol such as RELIANCE, TATAMOTORS or a sector like BANKS.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
