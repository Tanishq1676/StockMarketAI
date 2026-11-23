"use client";

import type { NewsItem } from "@/types";

export default function NewsList({ news }: { news: NewsItem[] }) {
  return (
    <section className="glass-card card-hover p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="card-title">Stock news {news[0]?.symbol ? `· ${news[0].symbol}` : ""}</h2>
          <p className="card-sub">Headlines with sentiment and impact scoring</p>
        </div>
        <span className="pill pill-flat">{news.length}</span>
      </div>

      {news.length ? (
        <ul className="mt-4 divide-y divide-line/60">
          {news.map((n, i) => {
            const score = typeof n.sentiment_score === "number" ? n.sentiment_score : null;
            return (
              <li key={n.link || i} className="py-3 first:pt-0 last:pb-0">
                <a
                  href={n.link}
                  target="_blank"
                  rel="noreferrer"
                  className="group flex items-start gap-3 rounded-xl px-1 py-1 transition-colors hover:bg-accent-soft/50"
                >
                  <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-[10px] font-extrabold text-accent-dark">
                    {(n.source || "N").slice(0, 1).toUpperCase()}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold leading-snug text-ink transition-colors group-hover:text-accent-dark">
                      {n.title}
                    </span>
                    <span className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-fg-muted">
                      <span>{n.source}</span>
                      {n.published_at && (
                        <span className="text-fg-dim" suppressHydrationWarning>
                          {new Date(n.published_at).toLocaleString("en-IN", {
                            day: "2-digit",
                            month: "short",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      )}
                      {score != null && (
                        <span
                          className={`pill !px-2 !py-0.5 !text-[10px] ${
                            score > 0 ? "pill-up" : score < 0 ? "pill-down" : "pill-flat"
                          }`}
                        >
                          {score > 0 ? "▲" : score < 0 ? "▼" : "•"} {score > 0 ? "+" : ""}
                          {score.toFixed(2)}
                        </span>
                      )}
                      {n.impact && (
                        <span className="chip !px-2 !py-0.5 !text-[10px] capitalize">{n.impact}</span>
                      )}
                    </span>
                  </span>
                </a>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="mt-4 rounded-xl border border-dashed border-line bg-white/40 px-4 py-8 text-center text-xs text-fg-muted">
          No news articles for this stock yet.
        </div>
      )}
    </section>
  );
}
