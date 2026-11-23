"use client";

const sourceTone = (source: string) => {
  const s = (source || "").toLowerCase();
  if (s.includes("economic")) return "bg-[#EDF4FF] text-[#2B5A9B]";
  if (s.includes("money")) return "bg-[#FFF4E8] text-[#9A5B12]";
  if (s.includes("mint")) return "bg-[#EAF8F1] text-[#0A6B49]";
  if (s.includes("business")) return "bg-[#F3EEFF] text-[#5B3E9B]";
  return "bg-surface-2 text-fg-muted";
};

const when = (value?: string) => {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const SOURCE_LABELS = ["Economic Times", "Moneycontrol", "Business Standard", "Mint", "NDTV Profit"];

export default function NewsFeed({ news, limit = 12 }: { news: any[]; limit?: number }) {
  if (!news.length) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-white/40 px-4 py-9 text-center">
        <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 5.5A1.5 1.5 0 015.5 4H17a1.5 1.5 0 011.5 1.5V18a2 2 0 002 2H6a2 2 0 01-2-2V5.5z" />
            <path d="M8 8h6.5M8 11.5h6.5M8 15h4" />
          </svg>
        </span>
        <p className="mt-3 text-sm font-semibold text-fg">No headlines cached right now</p>
        <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-fg-muted">
          The desk aggregates Indian market coverage from five publishers. Headlines appear here
          as soon as the news feed is reachable.
        </p>
        <div className="mt-3 flex flex-wrap items-center justify-center gap-1.5">
          {SOURCE_LABELS.map((s) => (
            <span key={s} className="chip !px-2 !py-0.5 !text-[10px]">
              {s}
            </span>
          ))}
        </div>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-line/60">
      {news.slice(0, limit).map((n: any, i: number) => {
        const score = typeof n.sentiment_score === "number" ? n.sentiment_score : null;
        return (
          <li key={n.link || i} className="group py-3 first:pt-0 last:pb-0">
            <a
              href={n.link}
              target="_blank"
              rel="noreferrer"
              className="flex gap-3 rounded-xl px-1 py-1 transition-colors hover:bg-accent-soft/50"
            >
              <span
                className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[11px] font-extrabold ${sourceTone(n.source)}`}
                aria-hidden
              >
                {(n.source || "N").slice(0, 1).toUpperCase()}
              </span>
              <span className="min-w-0 flex-1">
                <span className="line-clamp-2 text-sm font-semibold leading-snug text-ink transition-colors group-hover:text-accent-dark">
                  {n.title}
                </span>
                <span className="mt-1.5 flex flex-wrap items-center gap-2 text-[11px] text-fg-muted">
                  <span className="font-semibold text-fg-muted">{n.source}</span>
                  {n.published_at && (
                    <>
                      <span className="text-fg-dim" aria-hidden>
                        ·
                      </span>
                      <span suppressHydrationWarning>{when(n.published_at)}</span>
                    </>
                  )}
                  {n.symbol && (
                    <span className="rounded-md bg-accent-soft px-1.5 py-0.5 text-[10px] font-bold text-accent-dark">
                      {n.symbol}
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
              <span className="mt-1 shrink-0 text-fg-dim transition-colors group-hover:text-accent" aria-hidden>
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M7 17L17 7M9 7h8v8" />
                </svg>
              </span>
            </a>
          </li>
        );
      })}
    </ul>
  );
}
