"use client";

import type { Signal } from "@/types";

function fmt(v: any) {
  return v == null ? "—" : typeof v === "number" ? v.toLocaleString("en-IN", { maximumFractionDigits: 4 }) : "—";
}

const TONE: Record<string, { card: string; badge: string; bar: string; icon: string }> = {
  BUY: {
    card: "border-up/20 bg-up/5",
    badge: "bg-up/10 text-up border-up/20",
    bar: "bg-up",
    icon: "↗",
  },
  SELL: {
    card: "border-down/20 bg-down/5",
    badge: "bg-down/10 text-down border-down/20",
    bar: "bg-down",
    icon: "↘",
  },
  HOLD: {
    card: "border-line bg-surface-0/60",
    badge: "bg-surface-2 text-fg-muted border-line",
    bar: "bg-fg-dim",
    icon: "→",
  },
  WAIT_FOR_CONFIRMATION: {
    card: "border-warn/20 bg-warn/5",
    badge: "bg-warn/10 text-warn border-warn/20",
    bar: "bg-warn",
    icon: "◷",
  },
};

const SHORT: Record<string, string> = {
  WAIT_FOR_CONFIRMATION: "WAIT",
};

export default function SignalPanel({
  signal,
  onGenerate,
  generating,
}: {
  signal: Signal | null;
  onGenerate: () => void;
  generating: boolean;
}) {
  if (!signal) {
    return (
      <div className="glass-card card-hover flex flex-col p-5 sm:p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="card-title">BUY / SELL / HOLD signal</h2>
            <p className="card-sub">Rule-engine technical + sentiment model</p>
          </div>
          <span className="pill pill-flat">Awaiting run</span>
        </div>
        <div className="mt-5 flex flex-1 flex-col items-center justify-center rounded-2xl border border-dashed border-line bg-white/40 px-5 py-10 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent">
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 17l6-6 4 3 6-7" />
              <path d="M15 7h5v5" />
            </svg>
          </span>
          <p className="mt-3 text-sm font-semibold text-ink">
            {generating ? "Generating signal…" : "No signal generated yet"}
          </p>
          <p className="mt-1 max-w-xs text-xs leading-relaxed text-fg-muted">
            Run the engine to combine trend, momentum, volatility and news sentiment.
          </p>
          <button onClick={onGenerate} disabled={generating} className="btn btn-primary mt-4">
            {generating ? "Generating…" : "Generate signal"}
          </button>
        </div>
      </div>
    );
  }

  const tone = TONE[signal.signal_type] || TONE.HOLD;
  const confidence =
    typeof signal.confidence === "number" ? Math.max(0, Math.min(1, signal.confidence)) : null;

  const metrics: [string, string][] = [
    ["Entry price", fmt(signal.entry_price)],
    ["Target price", fmt(signal.target_price)],
    ["Stop loss", fmt(signal.stop_loss)],
    ["Risk / reward", fmt(signal.risk_reward)],
    [
      "Expected holding",
      signal.expected_holding_minutes ? `${signal.expected_holding_minutes} min` : "—",
    ],
    ["Risk level", signal.risk_level ? String(signal.risk_level) : "—"],
    ["Confidence", confidence != null ? `${(confidence * 100).toFixed(1)}%` : "—"],
    [
      "News sentiment",
      signal.news_sentinel_score != null
        ? `${signal.news_sentinel_score >= 0 ? "+" : ""}${signal.news_sentinel_score.toFixed(2)}`
        : "—",
    ],
  ];

  return (
    <div className="glass-card card-hover flex flex-col p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="card-title">BUY / SELL / HOLD signal</h2>
          <p className="card-sub">Rule-engine technical + sentiment model</p>
        </div>
        <button
          onClick={onGenerate}
          disabled={generating}
          className="btn btn-ghost btn-xs"
        >
          {generating ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div className={`mt-4 rounded-2xl border p-4 ${tone.card}`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className={`inline-flex shrink-0 items-center gap-2 rounded-xl border px-3 py-1.5 text-sm font-extrabold ${tone.badge}`}>
            <span aria-hidden>{tone.icon}</span>
            {SHORT[signal.signal_type] || signal.signal_type}
          </span>
          <span className="shrink-0 text-right">
            <span className="metric-label">Confidence</span>
            <span className="num block text-lg font-extrabold text-ink">
              {confidence != null ? `${Math.round(confidence * 100)}%` : "—"}
            </span>
          </span>
        </div>
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-white/70">
          <span
            className={`block h-full rounded-full transition-all duration-700 ${tone.bar}`}
            style={{ width: `${confidence != null ? confidence * 100 : 0}%` }}
          />
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2 text-center">
          <div>
            <p className="metric-label">Entry</p>
            <p className="num text-sm font-bold text-ink">{fmt(signal.entry_price)}</p>
          </div>
          <div>
            <p className="metric-label">Target</p>
            <p className="num text-sm font-bold text-up">{fmt(signal.target_price)}</p>
          </div>
          <div>
            <p className="metric-label">Stop</p>
            <p className="num text-sm font-bold text-down">{fmt(signal.stop_loss)}</p>
          </div>
        </div>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2.5">
        {metrics.slice(3).map(([k, v]) => (
          <div key={k} className="flex items-baseline justify-between gap-2 border-b border-line/50 pb-2">
            <dt className="text-[11px] text-fg-muted">{k}</dt>
            <dd className="num text-right text-xs font-semibold text-ink">{v}</dd>
          </div>
        ))}
      </dl>

      {(signal.reasons || []).length ? (
        <div className="mt-4">
          <p className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.16em] text-fg-dim">
            Rationale
          </p>
          <ul className="space-y-1">
            {signal.reasons.slice(0, 4).map((r: string, i: number) => (
              <li key={i} className="flex gap-2 text-xs leading-relaxed text-fg-muted">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden />
                {r}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {signal.ai_summary ? (
        <p className="mt-3 rounded-xl bg-accent-soft/70 px-3 py-2.5 text-xs leading-relaxed text-accent-dark">
          {signal.ai_summary}
        </p>
      ) : null}

      <div className="mt-auto pt-4">
        <p className="text-[10px] leading-relaxed text-fg-dim" suppressHydrationWarning>
          Generated {signal.generated_at ? new Date(signal.generated_at).toLocaleString("en-IN") : "—"} · source{" "}
          {signal.ai_source || "rule engine"}. Forecast-based; confirm before acting.
        </p>
      </div>
    </div>
  );
}
