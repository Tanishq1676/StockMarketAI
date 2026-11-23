"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import type { HistoryRow, Analysis, Quote, Signal, Prediction, Meta } from "@/types";
import { api } from "@/lib/api";
import {
  DATA_MODE_LABEL,
  dataMode,
  formatSessionDate,
  formatSessionShort,
  formatTimestampIst,
  sourceLabel,
} from "@/lib/market";
import Chart from "@/components/Chart";
import IndicatorsPanel from "@/components/IndicatorsPanel";
import SignalPanel from "@/components/SignalPanel";
import PredictionPanel from "@/components/PredictionPanel";
import NewsList from "@/components/NewsList";

const fmt = (v: any, digits = 2) =>
  typeof v === "number" ? v.toLocaleString("en-IN", { maximumFractionDigits: digits }) : "—";

const MA_PERIODS = [20, 50];

export default function StockDetailView(props: {
  symbol: string;
  meta: Meta;
  quote: Quote | null;
  history: HistoryRow[];
  analysis?: Analysis | null;
  signal?: Signal | null;
  predictions?: Prediction[];
}) {
  const { symbol, meta, history, signal, predictions } = props;
  const analysis: Analysis = props.analysis || ({} as Analysis);
  const [quote, setQuote] = useState<Quote | null>(props.quote);
  const [sig, setSig] = useState<Signal | null>(signal || null);
  const [generating, setGenerating] = useState(false);
  const preds = predictions || [];

  useEffect(() => {
    const t = setInterval(async () => {
      try {
        const d = await api.get<any>(`/api/stocks/${symbol}`);
        if (d?.quote) setQuote(d.quote);
      } catch {
        /* keep the last quote */
      }
    }, 60_000);
    return () => clearInterval(t);
  }, [symbol]);

  const gen = async () => {
    setGenerating(true);
    try {
      const d = await api.post<any>(`/api/signals/generate/${symbol}`);
      setSig(d.signal);
    } catch {
      /* leave the existing signal in place */
    } finally {
      setGenerating(false);
    }
  };

  const change = typeof quote?.change_pct === "number" ? quote.change_pct : null;
  const up = change != null && change > 0;
  const down = change != null && change < 0;
  const mode = dataMode(quote);
  const prevClose =
    typeof quote?.prev_close === "number"
      ? quote.prev_close
      : history.length >= 2
        ? history[history.length - 2].close
        : null;
  const sentiment =
    typeof analysis.sentiment_score === "number" ? analysis.sentiment_score : null;

  const stats: [string, string][] = [
    ["Open", fmt(quote?.open)],
    ["High", fmt(quote?.high)],
    ["Low", fmt(quote?.low)],
    ["Prev. close", fmt(prevClose)],
    ["Volume", fmt(quote?.volume, 0)],
    ["Session", formatSessionShort(quote?.trade_date)],
  ];

  return (
    <main className="page">
      <div className="flex flex-col gap-5">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-xs text-fg-muted" aria-label="Breadcrumb">
          <Link href="/" className="transition-colors hover:text-accent-dark">
            Dashboard
          </Link>
          <span className="text-fg-dim" aria-hidden>
            /
          </span>
          <Link href="/stocks" className="transition-colors hover:text-accent-dark">
            All stocks
          </Link>
          <span className="text-fg-dim" aria-hidden>
            /
          </span>
          <span className="font-semibold text-ink">{symbol}</span>
        </nav>

        {/* Hero */}
        <section className="glass-card glow-emerald p-5 sm:p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="pill pill-accent">{symbol}</span>
                <span className="chip !py-0.5">{meta.exchange || "NSE"}</span>
                {meta.sector && <span className="chip !py-0.5">{meta.sector}</span>}
                {meta.market_cap && (
                  <span className="chip !py-0.5 capitalize">{meta.market_cap} cap</span>
                )}
              </div>
              <h1 className="mt-3 text-[1.6rem] font-extrabold leading-tight tracking-tight text-ink sm:text-[2rem]">
                {meta.name}
              </h1>
              <div className="mt-3 flex flex-wrap items-end gap-x-4 gap-y-2">
                <div className="flex flex-col">
                  <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-fg-dim">
                    {mode === "live" ? "Live price" : "Last close"}
                  </span>
                  <span className="num text-[2.2rem] font-extrabold leading-none tracking-tight text-ink">
                    ₹{fmt(quote?.close)}
                  </span>
                </div>
                <span className={`pill ${up ? "pill-up" : down ? "pill-down" : "pill-flat"}`}>
                  {up ? "▲" : down ? "▼" : "•"}{" "}
                  {change != null ? `${change > 0 ? "+" : ""}${change.toFixed(2)}%` : "—"}
                </span>
                <span className="flex flex-col gap-0.5 pb-1 text-[11px] text-fg-dim" suppressHydrationWarning>
                  <span className="inline-flex flex-wrap items-center gap-1.5">
                    <span className={`pill !px-2 !py-0.5 !text-[10px] ${mode === "live" ? "pill-up" : "pill-flat"}`}>
                      {DATA_MODE_LABEL[mode]}
                    </span>
                    <span>Session {formatSessionDate(quote?.trade_date)}</span>
                  </span>
                  <span>
                    {quote?.fetched_at || quote?.last_updated
                      ? `Fetched ${formatTimestampIst(quote?.fetched_at || quote?.last_updated)}`
                      : "Fetch time unavailable"}
                    {" · "}
                    {sourceLabel(quote?.data_source)}
                  </span>
                </span>
              </div>
            </div>

            <div className="flex shrink-0 flex-wrap gap-2">
              <Link href="/stocks" className="btn btn-ghost">
                Back to stocks
              </Link>
              <button onClick={gen} disabled={generating} className="btn btn-primary">
                {generating ? "Generating…" : "Generate signal"}
              </button>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-2 border-t border-line/70 pt-4 sm:grid-cols-3 lg:grid-cols-6">
            {stats.map(([k, v]) => (
              <div key={k} className="rounded-xl bg-white/50 px-3 py-2.5">
                <p className="metric-label">{k}</p>
                <p className="num mt-0.5 text-sm font-bold text-ink">{v}</p>
              </div>
            ))}
          </div>

          {meta.nse_indices?.length ? (
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-fg-dim">
                Part of
              </span>
              {meta.nse_indices.slice(0, 8).map((idx) => (
                <span key={idx} className="chip !py-0.5 !text-[10px]">
                  {idx}
                </span>
              ))}
            </div>
          ) : null}
        </section>

        {/* Chart */}
        <section className="glass-card p-5 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="card-title">{symbol} · Daily candles</h2>
              <p className="card-sub">Price history with 20 &amp; 50-day moving averages</p>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-[11px] text-fg-muted">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-up" /> Up
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-down" /> Down
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-[2px] w-4 rounded-full bg-[#C08A2E]" /> MA 20
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-[2px] w-4 rounded-full bg-accent" /> MA 50
              </span>
            </div>
          </div>
          <Chart series={history} mas={MA_PERIODS} height={400} />
        </section>

        {/* Indicators + signal */}
        <div className="grid gap-4 xl:grid-cols-3">
          <div className="xl:col-span-2">
            <IndicatorsPanel analysis={analysis} />
          </div>
          <SignalPanel signal={sig} onGenerate={gen} generating={generating} />
        </div>

        {/* Predictions + AI analysis */}
        <div className="grid gap-4 xl:grid-cols-3">
          <div className="xl:col-span-2">
            <PredictionPanel symbol={symbol} predictions={preds} />
          </div>

          <section className="glass-card card-hover flex flex-col p-5 sm:p-6">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="card-title">AI analysis</h2>
                <p className="card-sub">Narrative research summary</p>
              </div>
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3l1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9L12 3z" />
                  <path d="M18 15l.9 2.1L21 18l-2.1.9L18 21l-.9-2.1L15 18l2.1-.9L18 15z" />
                </svg>
              </span>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span
                className={`pill ${
                  sentiment == null
                    ? "pill-flat"
                    : sentiment > 0
                      ? "pill-up"
                      : sentiment < 0
                        ? "pill-down"
                        : "pill-flat"
                }`}
              >
                {sentiment == null ? "•" : sentiment > 0 ? "▲" : sentiment < 0 ? "▼" : "•"} Sentiment{" "}
                {sentiment != null ? `${sentiment >= 0 ? "+" : ""}${sentiment.toFixed(2)}` : "n/a"}
              </span>
              {analysis.ai_source && <span className="chip !py-0.5">{analysis.ai_source}</span>}
            </div>

            <p className="mt-3 flex-1 text-sm leading-relaxed text-fg-muted">
              {analysis.ai_summary || "No AI narrative is available for this symbol yet."}
            </p>

            {analysis.ai_risk_factors?.length ? (
              <div className="mt-3">
                <p className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.16em] text-fg-dim">
                  Risk factors
                </p>
                <ul className="space-y-1">
                  {analysis.ai_risk_factors.slice(0, 5).map((f: string, i: number) => (
                    <li key={i} className="flex gap-2 text-xs leading-relaxed text-down/90">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-down" aria-hidden />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
        </div>

        <NewsList news={analysis.news || []} />
      </div>
    </main>
  );
}
