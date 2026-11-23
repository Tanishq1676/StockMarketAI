"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { NewsItem } from "@/types";
import PageHeader from "@/components/PageHeader";
import NewsFeed from "@/components/NewsFeed";

export const dynamic = "force-dynamic";

export default function NewsPage() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const d = await api.get<any>("/api/news?limit=30");
        setNews(d.news || []);
      } catch {
        /* empty state is handled below */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const sentiment = useMemo(() => {
    const positive = news.filter((n) => (n.sentiment_score ?? 0) > 0).length;
    const negative = news.filter((n) => (n.sentiment_score ?? 0) < 0).length;
    const neutral = Math.max(0, news.length - positive - negative);
    return { positive, negative, neutral, total: news.length || 1 };
  }, [news]);

  const sources = useMemo(() => {
    const counts = new Map<string, number>();
    news.forEach((n) => {
      const key = n.source || "Other";
      counts.set(key, (counts.get(key) || 0) + 1);
    });
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
  }, [news]);

  return (
    <main className="page">
      <PageHeader
        eyebrow="Markets"
        title="Financial news"
        description="Coverage from Economic Times, Moneycontrol, Business Standard, Mint and NDTV Profit — each article scored for sentiment and market impact."
      >
        <span className="pill pill-accent">{news.length} articles</span>
        <span className="pill pill-flat">Sentiment scored</span>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-3">
        <section className="glass-card card-hover p-5 sm:p-6 xl:col-span-2">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="card-title">Latest headlines</h2>
              <p className="card-sub">Newest first · opens the original source</p>
            </div>
            <span className="pill pill-flat">{news.length}</span>
          </div>

          <div className="mt-4">
            {loading ? (
              <div className="space-y-3">
                {[0, 1, 2, 3, 4].map((i) => (
                  <div key={i} className="flex gap-3">
                    <div className="skeleton h-9 w-9 shrink-0 rounded-lg" />
                    <div className="flex-1 space-y-2">
                      <div className="skeleton h-4 w-4/5" />
                      <div className="skeleton h-3 w-2/5" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <NewsFeed news={news} limit={30} />
            )}
          </div>
        </section>

        <aside className="flex flex-col gap-4">
          <section className="glass-card card-pad">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="card-title">Sentiment mix</h2>
                <p className="card-sub">Across the latest articles</p>
              </div>
              <span className="pill pill-accent">NLP</span>
            </div>

            <div className="mt-4 flex h-2.5 w-full overflow-hidden rounded-full bg-surface-2">
              <span className="block h-full bg-up" style={{ width: `${(sentiment.positive / sentiment.total) * 100}%` }} />
              <span className="block h-full bg-fg-dim" style={{ width: `${(sentiment.neutral / sentiment.total) * 100}%` }} />
              <span className="block h-full bg-down" style={{ width: `${(sentiment.negative / sentiment.total) * 100}%` }} />
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2">
              {[
                { label: "Positive", value: sentiment.positive, tone: "text-up", dot: "bg-up" },
                { label: "Neutral", value: sentiment.neutral, tone: "text-fg-muted", dot: "bg-fg-dim" },
                { label: "Negative", value: sentiment.negative, tone: "text-down", dot: "bg-down" },
              ].map((s) => (
                <div key={s.label} className="rounded-xl border border-line/60 bg-white/50 px-2.5 py-2">
                  <span className={`inline-flex items-center gap-1.5 text-[10px] font-semibold ${s.tone}`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} aria-hidden />
                    {s.label}
                  </span>
                  <p className="num mt-1 text-lg font-extrabold text-ink">{s.value}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="glass-card card-pad">
            <h2 className="card-title">Sources</h2>
            <p className="card-sub">Publication mix in the current feed</p>
            {sources.length ? (
              <ul className="mt-4 space-y-2.5">
                {sources.map(([source, count]) => (
                  <li key={source}>
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-fg-muted">{source}</span>
                      <span className="num font-bold text-ink">{count}</span>
                    </div>
                    <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                      <span
                        className="block h-full rounded-full bg-accent"
                        style={{ width: `${(count / (sources[0]?.[1] || 1)) * 100}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-xs text-fg-muted">Waiting for the news feed…</p>
            )}
          </section>

          <section className="glass-card card-pad">
            <h2 className="card-title">How scoring works</h2>
            <p className="mt-2 text-xs leading-relaxed text-fg-muted">
              Headlines are scored for directional sentiment and impact, then mapped to related symbols and
              sectors. Scores feed the signal engine alongside technical indicators — they are not trading
              recommendations.
            </p>
          </section>
        </aside>
      </div>
    </main>
  );
}
