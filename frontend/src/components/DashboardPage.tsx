"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import SearchBar from "@/components/SearchBar";
import useLiveUpdates from "@/hooks/useLiveUpdates";
import IndexTiles from "@/components/IndexTiles";
import SnapshotTable from "@/components/SnapshotTable";
import NewsFeed from "@/components/NewsFeed";
import AlertsPanel from "@/components/AlertsPanel";
import Chart from "@/components/Chart";
import Watchlist from "@/components/Watchlist";
import type { DataStatus } from "@/types";
import {
  formatSessionDate,
  formatTimestampIst,
} from "@/lib/market";

const money = (v: any) =>
  typeof v === "number" ? `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 2 })}` : "—";

const pct = (v: any) =>
  typeof v === "number" ? `${v > 0 ? "+" : ""}${v.toFixed(2)}%` : "—";

const NIFTY_MAS = [20, 50];

const INDEX_PRIORITY = ["NIFTY50", "SENSEX", "BANKNIFTY", "NIFTY100", "NIFTY500", "NIFTYNEXT50"];

function pickIndices(rows: any[], limit = 6) {
  const list = Array.isArray(rows) ? rows : [];
  const lead = INDEX_PRIORITY.map((symbol) => list.find((i) => i?.symbol === symbol)).filter(
    Boolean
  ) as any[];
  const rest = list.filter((i) => !INDEX_PRIORITY.includes(i?.symbol));
  return [...lead, ...rest].slice(0, limit);
}

export default function DashboardPage({ initial }: { initial?: any }) {
  const { live } = useLiveUpdates();
  const [data, setData] = useState<any>(initial || null);
  const [nifty, setNifty] = useState<any>(null);
  const [err, setErr] = useState("");

  const refresh = useCallback(async () => {
    try {
      const d = await api.get<any>("/api/dashboard");
      setData(d);
      setErr("");
    } catch (e: any) {
      setErr(e?.message || "fetch failed");
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 60_000);
    return () => clearInterval(t);
  }, [refresh]);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const d = await api.get<any>("/api/stocks/NIFTY50");
        if (alive) setNifty(d);
      } catch {
        /* chart simply stays in its loading state */
      }
    };
    load();
    const t = setInterval(load, 60_000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  const snap = data?.snapshot || live || {
    indices: [],
    top_gainers: [],
    top_losers: [],
    most_active: [],
    unusual_volume: [],
  };
  const s = (arr: any[]) => (Array.isArray(arr) ? arr.slice(0, 6) : []);
  const updated = data?.snapshot?.updated_at || live?.updatedAt;

  const niftyHistory = Array.isArray(nifty?.history) ? nifty.history : [];
  const niftyQuote = nifty?.quote;
  const niftyChange =
    typeof niftyQuote?.change_pct === "number" ? niftyQuote.change_pct : null;

  return (
    <main className="page">
      <div className="flex flex-col gap-6">
        {/* Hero */}
        <header className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div className="animate-fade-up">
            <span className="eyebrow">
              <span className="live-dot" />
              Market intelligence
            </span>
            <h1 className="h1 mt-2.5">Market overview</h1>
            <p className="sub mt-2 max-w-2xl">
              An AI-assisted research desk for NSE &amp; BSE equities — live snapshots,
              technical signals, forecasts, news sentiment and portfolio performance in one view.
            </p>
          </div>
          <div className="w-full animate-fade-up stagger-2 xl:max-w-md">
            <SearchBar />
            <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 px-1 text-[11px] text-fg-dim">
              <span className="inline-flex items-center gap-1.5">
                <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round">
                  <circle cx="12" cy="12" r="8.5" />
                  <path d="M12 7.5V12l3 2" />
                </svg>
                <span suppressHydrationWarning>
                  {updated ? `Snapshot built ${formatTimestampIst(updated)}` : "Syncing market data…"}
                </span>
              </span>
              <span className="pill pill-accent">Auto-refresh · 60s</span>
            </div>
          </div>
        </header>

        {err && (
          <div className="flex items-start gap-3 rounded-2xl border border-down/20 bg-down/5 px-4 py-3 text-sm text-down">
            <span className="mt-0.5 font-bold" aria-hidden>
              !
            </span>
            <span>
              Live refresh failed — showing the last available snapshot. <span className="text-down/70">({err})</span>
            </span>
          </div>
        )}

        <DataStatusBanner status={data?.snapshot?.data_status} />

        {/* Indices */}
        <IndexTiles indices={pickIndices(snap.indices || [])} />

        {/* Chart + AI summary */}
        <div className="grid gap-4 xl:grid-cols-3">
          <section className="glass-card p-5 sm:p-6 xl:col-span-2">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="card-title">NIFTY 50 · Price action</h2>
                <p className="card-sub">Candlesticks with 20 &amp; 50-day moving averages</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <p className="metric-label">Last close</p>
                  <p className="num text-xl font-extrabold text-ink">
                    {niftyQuote?.close != null ? niftyQuote.close.toLocaleString("en-IN") : "—"}
                  </p>
                </div>
                <span
                  className={`pill ${
                    niftyChange == null
                      ? "pill-flat"
                      : niftyChange > 0
                        ? "pill-up"
                        : niftyChange < 0
                          ? "pill-down"
                          : "pill-flat"
                  }`}
                >
                  {niftyChange != null ? (niftyChange > 0 ? "▲" : niftyChange < 0 ? "▼" : "•") : "•"}{" "}
                  {pct(niftyChange)}
                </span>
              </div>
            </div>

            <Chart series={niftyHistory} mas={NIFTY_MAS} height={332} />

            <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] text-fg-muted">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-up" /> Up candle
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-down" /> Down candle
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-[2px] w-4 rounded-full bg-[#C08A2E]" /> MA 20
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-[2px] w-4 rounded-full bg-accent" /> MA 50
              </span>
            </div>
          </section>

          <section className="glass-card glow-emerald flex flex-col p-5 sm:p-6">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="card-title">AI market summary</h2>
                <p className="card-sub">Rule-engine research baseline</p>
              </div>
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3l1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9L12 3z" />
                  <path d="M18 15l.9 2.1L21 18l-2.1.9L18 21l-.9-2.1L15 18l2.1-.9L18 15z" />
                </svg>
              </span>
            </div>
            <p className="mt-4 flex-1 text-sm leading-relaxed text-fg-muted">
              {data?.ai_market_summary || live?.summary || "Analysing market breadth, momentum and news sentiment…"}
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-line/70 pt-4">
              <span className="pill pill-accent">
                <span aria-hidden>✦</span> AI research
              </span>
              {data?.ai_summary_source && (
                <span className="text-[11px] text-fg-dim">Source · {data.ai_summary_source}</span>
              )}
            </div>
          </section>
        </div>

        {/* Portfolio performance */}
        <PortfolioSection data={data} />

        {/* Movers */}
        <section>
          <div className="mb-3 flex items-end justify-between gap-3">
            <div>
              <h2 className="card-title">Market movers</h2>
              <p className="card-sub">Gainers, losers, activity and volume anomalies</p>
            </div>
            <Link href="/stocks" className="text-xs font-semibold text-accent hover:text-accent-dark">
              View all stocks →
            </Link>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <SnapshotTable title="Top Gainers" rows={s(snap.top_gainers || [])} />
            <SnapshotTable title="Top Losers" rows={s(snap.top_losers || [])} />
            <SnapshotTable title="Most Active" rows={s(snap.most_active || [])} />
            <SnapshotTable title="Unusual Volume" rows={s(snap.unusual_volume || [])} />
          </div>
        </section>

        {/* Signals + watchlist */}
        <div className="grid gap-4 xl:grid-cols-3">
          <section className="glass-card card-hover p-5 sm:p-6 xl:col-span-2">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="card-title">Top AI signals</h2>
                <p className="card-sub">Highest-confidence calls across the universe</p>
              </div>
              <span className="pill pill-accent !text-[10px]">BUY · SELL · HOLD</span>
            </div>
            <div className="mt-4">
              <SignalTable signals={(data?.top_signals || []) as any[]} />
            </div>
          </section>

          <Watchlist />
        </div>

        {/* News */}
        <section className="glass-card card-hover p-5 sm:p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="card-title">Latest financial news</h2>
              <p className="card-sub">Indian market coverage with sentiment scoring</p>
            </div>
            <Link href="/news" className="text-xs font-semibold text-accent hover:text-accent-dark">
              All news →
            </Link>
          </div>
          <div className="mt-4">
            <NewsFeed news={(data?.latest_news || []) as any[]} />
          </div>
        </section>

        <AlertsPanel />
      </div>
    </main>
  );
}

function DataStatusBanner({ status }: { status?: DataStatus }) {
  const officialSources = (status?.sources || []).filter(
    (s) => s !== "demo" && s !== "provider"
  );
  const hasOfficial = officialSources.length > 0;
  const live = !!status?.is_live;
  return (
    <section
      className={`flex flex-col gap-2 rounded-2xl border px-4 py-3 text-xs sm:flex-row sm:items-center sm:justify-between ${
        hasOfficial ? "border-accent/20 bg-accent-soft/60" : "border-warn/30 bg-warn/5"
      }`}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <span className={`pill !text-[10px] ${hasOfficial ? "pill-accent" : "pill-warn"}`}>
          {hasOfficial ? "Official NSE / BSE data" : "No official data loaded"}
        </span>
        <span className="font-semibold text-ink">
          {status?.latest_trade_date
            ? `Session ${formatSessionDate(status.latest_trade_date)}`
            : "Session pending"}
        </span>
        <span className="text-fg-muted">
          · {live ? "Live quotes" : "Latest closing prices (not live intraday)"}
        </span>
      </div>
      <span className="text-[11px] text-fg-dim" suppressHydrationWarning>
        {status?.fetched_at
          ? `Fetched ${formatTimestampIst(status.fetched_at)}`
          : "Fetch time unavailable"}
      </span>
    </section>
  );
}

function SignalTable({ signals }: { signals: any[] }) {
  if (!signals.length) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-white/40 px-4 py-10 text-center">
        <p className="text-sm font-semibold text-fg">No signals yet</p>
        <p className="mt-1 text-xs text-fg-muted">Signals are generated as the rule engine scans the market.</p>
      </div>
    );
  }

  const badge: Record<string, string> = {
    BUY: "pill-up",
    SELL: "pill-down",
    HOLD: "pill-flat",
    WAIT_FOR_CONFIRMATION: "pill-warn",
  };
  const short: Record<string, string> = {
    WAIT_FOR_CONFIRMATION: "WAIT",
  };

  return (
    <ul className="space-y-2">
      {signals.map((s: any) => {
        const conf = typeof s.confidence === "number" ? Math.max(0, Math.min(1, s.confidence)) : null;
        return (
          <li key={s.symbol}>
            <Link
              href={`/stocks/${s.symbol}`}
              className="group flex items-center gap-3 rounded-xl border border-line/70 bg-white/55 px-3 py-2.5 transition-all hover:border-accent/25 hover:bg-white"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-[11px] font-extrabold text-accent-dark">
                {String(s.symbol || "").slice(0, 3)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-bold text-ink transition-colors group-hover:text-accent-dark">
                  {s.symbol}
                </span>
                <span className="mt-1 flex items-center gap-2">
                  <span className="h-1.5 w-20 overflow-hidden rounded-full bg-surface-2">
                    <span
                      className="block h-full rounded-full bg-accent"
                      style={{ width: `${conf != null ? conf * 100 : 0}%` }}
                    />
                  </span>
                  <span className="text-[10px] font-medium text-fg-dim">
                    {conf != null ? `${Math.round(conf * 100)}% confidence` : "confidence n/a"}
                  </span>
                </span>
              </span>
              <span className={`pill shrink-0 ${badge[s.signal_type] || badge.HOLD}`}>
                {short[s.signal_type] || s.signal_type || "HOLD"}
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function PortfolioSection({ data }: { data: any }) {
  const ps = data?.portfolio_summary;
  if (!ps) {
    return (
      <section className="glass-card card-pad">
        <div className="flex items-center justify-between gap-3">
          <h2 className="card-title">Portfolio performance</h2>
          <Link href="/portfolio" className="text-xs font-semibold text-accent hover:text-accent-dark">
            Open portfolio →
          </Link>
        </div>
        <p className="mt-3 text-sm text-fg-muted">Portfolio data will appear here once transactions are recorded.</p>
      </section>
    );
  }

  const cards: { label: string; value: string; tone?: "up" | "down" | "neutral"; hint?: string }[] = [
    { label: "Total investment", value: money(ps.total_investment) },
    { label: "Portfolio value", value: money(ps.current_portfolio_value), hint: "Mark-to-market" },
    {
      label: "Unrealised PnL",
      value: money(ps.unrealised_pnl),
      tone: (ps.unrealised_pnl ?? 0) >= 0 ? "up" : "down",
      hint: (ps.unrealised_pnl ?? 0) >= 0 ? "Open gains" : "Open losses",
    },
    {
      label: "Realised PnL",
      value: money(ps.realised_pnl),
      tone: (ps.realised_pnl ?? 0) >= 0 ? "up" : "down",
      hint: "Closed positions",
    },
    {
      label: "Total PnL",
      value: money(ps.total_pnl),
      tone: (ps.total_pnl ?? 0) >= 0 ? "up" : "down",
      hint: "Realised + unrealised",
    },
  ];

  const ret = typeof ps.total_return_pct === "number" ? ps.total_return_pct : null;

  return (
    <section>
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h2 className="card-title">Portfolio performance</h2>
          <p className="card-sub">Live valuation of recorded holdings</p>
        </div>
        <Link href="/portfolio" className="text-xs font-semibold text-accent hover:text-accent-dark">
          Open portfolio →
        </Link>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        {cards.map((c) => (
          <div key={c.label} className="glass-card card-hover p-4">
            <p className="metric-label">{c.label}</p>
            <p
              className={`mt-1.5 text-lg font-extrabold num ${
                c.tone === "up" ? "text-up" : c.tone === "down" ? "text-down" : "text-ink"
              }`}
            >
              {c.value}
            </p>
            {c.hint && <p className="mt-1 text-[10px] font-medium text-fg-dim">{c.hint}</p>}
          </div>
        ))}

        <div className="relative overflow-hidden rounded-2xl border border-transparent bg-emerald-cta p-4 text-white shadow-emerald">
          <span aria-hidden className="pointer-events-none absolute -right-6 -top-8 h-24 w-24 rounded-full bg-white/10 blur-2xl" />
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-white/65">Total return</p>
          <p className="num mt-1.5 text-xl font-extrabold">
            {ret != null ? `${ret > 0 ? "+" : ""}${ret.toFixed(2)}%` : "—"}
          </p>
          <p className="mt-1 flex items-center gap-1 text-[10px] font-medium text-white/70">
            <span aria-hidden>{ret == null ? "•" : ret >= 0 ? "▲" : "▼"}</span>
            {ret == null ? "Not available" : ret >= 0 ? "Above invested cost" : "Below invested cost"}
          </p>
        </div>
      </div>
    </section>
  );
}
