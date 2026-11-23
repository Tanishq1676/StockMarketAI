"use client";

import Link from "next/link";
import { formatSessionShort } from "@/lib/market";

const SUBTITLE: Record<string, string> = {
  "Top Gainers": "Strongest movers this session",
  "Top Losers": "Weakest movers this session",
  "Most Active": "Highest traded volume",
  "Unusual Volume": "Volume vs 60-day average",
};

const fmt = (v: any) =>
  typeof v === "number" ? v.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "—";

const fmtVol = (v: any) => {
  if (typeof v !== "number") return "";
  if (v >= 1e7) return `${(v / 1e7).toFixed(2)} Cr`;
  if (v >= 1e5) return `${(v / 1e5).toFixed(2)} L`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return String(Math.round(v));
};

export default function SnapshotTable({ title, rows }: { title: string; rows: any[] }) {
  const isLoser = title.toLowerCase().includes("loser");
  const isVolume = title.toLowerCase().includes("volume") || title.toLowerCase().includes("active");

  return (
    <section className="glass-card card-hover p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span
            className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border ${
              isLoser
                ? "border-down/15 bg-down/10 text-down"
                : isVolume
                  ? "border-accent/15 bg-accent-soft text-accent"
                  : "border-up/15 bg-up/10 text-up"
            }`}
            aria-hidden
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              {isLoser ? <path d="M4 7l6 6 4-3 6 7M20 17h-4M20 17v-4" /> : <path d="M4 17l6-6 4 3 6-7M20 7h-4M20 7v4" />}
            </svg>
          </span>
          <div>
            <h2 className="text-sm font-bold text-ink">{title}</h2>
            <p className="mt-0.5 text-[11px] text-fg-dim">{SUBTITLE[title] || "Market snapshot"}</p>
          </div>
        </div>
        <span className="pill pill-flat">{rows.length}</span>
      </div>

      {rows.length ? (
        <ul className="mt-4 space-y-1">
          {rows.map((r: any, idx: number) => {
            const change = typeof r.change_pct === "number" ? r.change_pct : null;
            const up = change != null && change > 0;
            const down = change != null && change < 0;
            return (
              <li key={r.symbol}>
                <Link
                  href={`/stocks/${r.symbol}`}
                  className="group flex items-center gap-3 rounded-xl px-2 py-2 transition-colors hover:bg-accent-soft/70"
                >
                  <span className="w-4 shrink-0 text-[10px] font-bold text-fg-dim">
                    {String(idx + 1).padStart(2, "0")}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-bold text-ink transition-colors group-hover:text-accent-dark">
                      {r.symbol}
                    </span>
                    <span className="num block text-[11px] text-fg-dim">
                      ₹{fmt(r.price)}
                      {typeof r.volume === "number" && (
                        <span className="ml-1.5 text-fg-dim/80">· {fmtVol(r.volume)} vol</span>
                      )}
                      {title === "Unusual Volume" && typeof r.volume_ratio === "number" && (
                        <span className="ml-1.5 font-semibold text-accent-dark/80">· {r.volume_ratio.toFixed(1)}× avg</span>
                      )}
                      {r.trade_date && (
                        <span className="ml-1.5 text-fg-dim/80">· {formatSessionShort(r.trade_date)}</span>
                      )}
                    </span>
                  </span>
                  <span
                    className={`pill shrink-0 ${
                      up ? "pill-up" : down ? "pill-down" : "pill-flat"
                    }`}
                  >
                    {up ? "▲" : down ? "▼" : "•"}{" "}
                    {change != null ? `${change > 0 ? "+" : ""}${change.toFixed(2)}%` : "…"}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="mt-4 rounded-xl border border-dashed border-line bg-white/40 px-3 py-8 text-center text-xs text-fg-muted">
          No data yet.
        </div>
      )}
    </section>
  );
}
