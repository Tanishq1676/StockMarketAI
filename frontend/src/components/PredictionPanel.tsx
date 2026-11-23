"use client";

import type { Prediction } from "@/types";

const HORIZON_LABEL: Record<string, string> = {
  "15min": "15 min",
  "30min": "30 min",
  "1hour": "1 hour",
  "2hour": "2 hours",
  "1day": "1 day",
  "5days": "5 days",
};

const price = (n: any) =>
  typeof n === "number" ? n.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "—";

export default function PredictionPanel({
  symbol,
  predictions,
}: {
  symbol: string;
  predictions: Prediction[];
}) {
  if (!predictions.length) {
    return (
      <div className="glass-card card-hover p-5 sm:p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="card-title">Price predictions</h2>
            <p className="card-sub">Multi-horizon statistical forecasts</p>
          </div>
          <span className="pill pill-flat">No run</span>
        </div>
        <div className="mt-5 rounded-2xl border border-dashed border-line bg-white/40 px-4 py-10 text-center">
          <p className="text-sm font-semibold text-ink">No predictions generated yet</p>
          <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-fg-muted">
            Forecasts appear once the prediction service has run for {symbol}.
          </p>
        </div>
      </div>
    );
  }

  const rows = [...predictions].sort((a, b) => (a.horizon || "").localeCompare(b.horizon || ""));

  return (
    <div className="glass-card card-hover p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="card-title">Price predictions — {symbol}</h2>
          <p className="card-sub">Multi-horizon statistical forecasts</p>
        </div>
        <span className="pill pill-accent">{rows.length} horizons</span>
      </div>

      <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
        {rows.map((p) => {
          const base = typeof p.predicted_close === "number" ? p.predicted_close : null;
          const interval =
            Array.isArray(p.prediction_interval) &&
            typeof p.prediction_interval[0] === "number" &&
            typeof p.prediction_interval[1] === "number"
              ? p.prediction_interval
              : base != null
                ? [base * 0.97, base * 1.03]
                : null;
          const [lo, hi] = interval || [null, null];
          const up = p.direction === "up";
          const down = p.direction === "down";
          const bull =
            typeof p.bullish_probability === "number"
              ? Math.max(0, Math.min(1, p.bullish_probability))
              : null;
          const bear =
            typeof p.bearish_probability === "number"
              ? Math.max(0, Math.min(1, p.bearish_probability))
              : null;

          return (
            <div key={p.horizon} className="rounded-2xl border border-line/70 bg-white/55 p-3.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] font-bold uppercase tracking-[0.1em] text-fg-muted">
                  {HORIZON_LABEL[p.horizon] || p.horizon}
                </span>
                <span
                  className={`pill !px-2 !py-0.5 !text-[10px] ${
                    up ? "pill-up" : down ? "pill-down" : "pill-flat"
                  }`}
                >
                  {up ? "▲" : down ? "▼" : "•"} {(p.direction || "flat").toUpperCase()}
                </span>
              </div>

              <p className="num mt-2 text-lg font-extrabold text-ink">{price(p.predicted_close)}</p>
              <p className="num mt-0.5 text-[10px] text-fg-dim">
                Range {price(lo)} – {price(hi)}
              </p>

              <div className="mt-2.5 flex h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                <span
                  className="block h-full bg-up"
                  style={{ width: `${bull != null ? bull * 100 : 0}%` }}
                  title={`Bullish ${bull != null ? Math.round(bull * 100) : 0}%`}
                />
                <span
                  className="block h-full bg-down"
                  style={{ width: `${bear != null ? bear * 100 : 0}%` }}
                  title={`Bearish ${bear != null ? Math.round(bear * 100) : 0}%`}
                />
              </div>

              <div className="mt-2 flex items-center justify-between text-[10px] text-fg-muted">
                <span>
                  Bull <span className="font-bold text-up">{bull != null ? `${Math.round(bull * 100)}%` : "—"}</span>
                </span>
                <span>
                  Bear <span className="font-bold text-down">{bear != null ? `${Math.round(bear * 100)}%` : "—"}</span>
                </span>
                <span>
                  Move{" "}
                  <span
                    className={`num font-bold ${
                      p.expected_move_pct == null
                        ? "text-fg-muted"
                        : p.expected_move_pct >= 0
                          ? "text-up"
                          : "text-down"
                    }`}
                  >
                    {p.expected_move_pct != null
                      ? `${p.expected_move_pct >= 0 ? "+" : ""}${p.expected_move_pct.toFixed(2)}%`
                      : "—"}
                  </span>
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <p className="mt-4 text-[10px] leading-relaxed text-fg-dim">
        Forecasts are statistical model outputs; prediction intervals represent uncertainty, not exact prices.
      </p>
    </div>
  );
}
