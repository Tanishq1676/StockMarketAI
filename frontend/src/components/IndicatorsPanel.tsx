"use client";

import type { Analysis } from "@/types";

const fmt = (v: any) => (v == null ? "—" : typeof v === "number" ? v.toFixed(2) : "—");

export default function IndicatorsPanel({ analysis }: { analysis: Analysis }) {
  const rows: [string, any][] = [
    ["RSI(14)", analysis.rsi14_last],
    ["MACD", analysis.macd?.macd_last],
    ["MACD signal", analysis.macd?.signal_last],
    ["MACD histogram", analysis.macd?.hist_last],
    ["Bollinger upper", analysis.bollinger?.upper_last],
    ["Bollinger middle", analysis.bollinger?.middle_last],
    ["Bollinger lower", analysis.bollinger?.lower_last],
    ["ATR(14)", analysis.atr14_last],
    ["Volatility (ann.)", analysis.historical_volatility_annualized],
    ["Max drawdown", analysis.max_drawdown_pct],
    ["Recent trend (20d)", analysis.recent_trend],
    ["Volume ratio (60d)", analysis.volume_ratio],
    ["Volume (last)", analysis.volume_last],
  ];

  const trend = typeof analysis.trend === "string" ? analysis.trend : null;
  const trendTone = trend
    ? /bull|up|positive/i.test(trend)
      ? "pill-up"
      : /bear|down|negative/i.test(trend)
        ? "pill-down"
        : "pill-flat"
    : "pill-flat";

  return (
    <section className="glass-card card-hover p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="card-title">Technical indicators</h2>
          <p className="card-sub">Momentum, volatility and trend structure</p>
        </div>
        <span className={`pill ${trendTone}`}>{trend || "No trend"}</span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {rows.map(([k, v]) => (
          <div key={k} className="rounded-xl border border-line/60 bg-white/50 px-3 py-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-fg-dim">{k}</p>
            <p className="num mt-0.5 text-sm font-bold text-ink">
              {k === "Volume (last)" && typeof v === "number"
                ? v.toLocaleString("en-IN", { maximumFractionDigits: 0 })
                : fmt(v)}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-4">
        <p className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.16em] text-fg-dim">
          Moving averages
        </p>
        <div className="flex flex-wrap gap-1.5">
          {(["ma5", "ma20", "ma50", "ma100", "ma200"] as const).map((k) => {
            const raw = analysis.ma?.[k]?.[0] ?? (analysis as any)[k];
            return (
              <span key={k} className="chip num">
                <span className="text-fg-dim">{k.toUpperCase()}</span>
                <span className="font-bold text-ink">{fmt(raw)}</span>
              </span>
            );
          })}
        </div>
      </div>

      <div className="mt-4 flex items-start gap-2 rounded-xl bg-surface-0/70 px-3 py-2.5">
        <span className="mt-0.5 text-accent" aria-hidden>
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round">
            <path d="M4 18h16M7 15V9M12 15V5M17 15v-4" />
          </svg>
        </span>
        <p className="text-[11px] leading-relaxed text-fg-muted">
          <span className="font-semibold text-ink">Support levels (approx.)</span>{" "}
          {(analysis.support_levels || [])
            .slice(0, 6)
            .map((l: number) => (typeof l === "number" ? l.toLocaleString("en-IN") : "—"))
            .join(", ") || "—"}
        </p>
      </div>
    </section>
  );
}
