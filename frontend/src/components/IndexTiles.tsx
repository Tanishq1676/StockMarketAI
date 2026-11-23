"use client";

import Link from "next/link";
import {
  DATA_MODE_LABEL,
  dataMode,
  formatSessionShort,
} from "@/lib/market";

const fmt = (v: any) => (typeof v === "number" ? v.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "—");
const pct = (v: any) =>
  typeof v === "number" ? `${v > 0 ? "+" : ""}${v.toFixed(2)}%` : "—";

export default function IndexTiles({ indices }: { indices: any[] }) {
  if (!indices.length) {
    return (
      <section className="glass-card card-pad">
        <h2 className="card-title">Major Indices</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="skeleton h-[132px] rounded-2xl" />
          ))}
        </div>
      </section>
    );
  }

  const advancing = indices.filter((i) => (i.change_pct ?? 0) > 0).length;
  const declining = indices.filter((i) => (i.change_pct ?? 0) < 0).length;

  const display = [...indices];
  const featureIdx = display.findIndex(
    (i) => i.symbol === "NIFTY50" || /^NIFTY\s*50$/i.test(i.name || "")
  );
  if (featureIdx > 0) {
    const [featureItem] = display.splice(featureIdx, 1);
    display.unshift(featureItem);
  }

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="card-title">Major Indices</h2>
          <p className="card-sub">NIFTY 50, SENSEX and key benchmarks</p>
        </div>
        <div className="flex items-center gap-2 text-[11px]">
          <span className="pill pill-up">
            <span aria-hidden>▲</span> {advancing} advancing
          </span>
          <span className="pill pill-down">
            <span aria-hidden>▼</span> {declining} declining
          </span>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {display.map((i: any, idx: number) => {
          const change = typeof i.change_pct === "number" ? i.change_pct : null;
          const up = change != null && change > 0;
          const down = change != null && change < 0;
          const feature = idx === 0;
          const width = change == null ? 0 : Math.min(Math.abs(change) * 9, 100);

          return (
            <Link
              key={i.symbol}
              href={`/stocks/${i.symbol}`}
              className={`group relative overflow-hidden rounded-2xl border p-4 transition-all duration-300 hover:-translate-y-0.5 ${
                feature
                  ? "border-transparent bg-emerald-cta text-white shadow-emerald hover:shadow-[0_18px_40px_-18px_rgba(10,107,73,0.75)]"
                  : "glass-card card-hover"
              }`}
            >
              {feature && (
                <span
                  aria-hidden
                  className="pointer-events-none absolute -right-8 -top-10 h-32 w-32 rounded-full bg-white/10 blur-2xl"
                />
              )}
              <div className="relative flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p
                    className={`truncate text-sm font-bold ${
                      feature ? "text-white" : "text-ink"
                    }`}
                  >
                    {i.name || i.symbol}
                  </p>
                  <p
                    className={`mt-0.5 text-[10px] font-bold uppercase tracking-[0.16em] ${
                      feature ? "text-white/60" : "text-fg-dim"
                    }`}
                  >
                    {i.symbol}
                  </p>
                </div>
                <span
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[13px] font-bold ${
                    feature
                      ? "bg-white/15 text-white"
                      : up
                        ? "bg-up/10 text-up"
                        : down
                          ? "bg-down/10 text-down"
                          : "bg-surface-2 text-fg-muted"
                  }`}
                  aria-hidden
                >
                  {up ? "↗" : down ? "↘" : "→"}
                </span>
              </div>

              <div className="relative mt-3 flex items-baseline justify-between gap-2">
                <span
                  className={`num text-[1.35rem] font-extrabold tracking-tight ${
                    feature ? "text-white" : "text-ink"
                  }`}
                >
                  {fmt(i.price)}
                </span>
                <span
                  className={`pill ${
                    feature
                      ? "bg-white/15 text-white"
                      : up
                        ? "pill-up"
                        : down
                          ? "pill-down"
                          : "pill-flat"
                  }`}
                >
                  {up ? "▲" : down ? "▼" : "•"} {pct(change)}
                </span>
              </div>

              <div className="relative mt-3">
                <div
                  className={`h-1.5 w-full overflow-hidden rounded-full ${
                    feature ? "bg-white/20" : "bg-surface-2"
                  }`}
                >
                  <span
                    className={`block h-full rounded-full transition-all duration-500 ${
                      feature ? "bg-white/80" : up ? "bg-up" : down ? "bg-down" : "bg-fg-dim"
                    }`}
                    style={{ width: `${width}%` }}
                  />
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <span
                    className={`text-[10px] font-medium ${
                      feature ? "text-white/65" : "text-fg-dim"
                    }`}
                  >
                    {i.trade_date
                      ? `${formatSessionShort(i.trade_date)} · ${DATA_MODE_LABEL[dataMode(i)].toLowerCase()}`
                      : feature
                        ? "Benchmark"
                        : "Session pending"}
                  </span>
                  <span
                    className={`text-[10px] font-semibold ${
                      feature ? "text-white/80" : up ? "text-up" : down ? "text-down" : "text-fg-muted"
                    }`}
                  >
                    {change != null ? (up ? "Gaining" : down ? "Declining" : "Flat") : "Loading"}
                  </span>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
