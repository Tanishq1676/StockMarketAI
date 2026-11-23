import PageHeader from "@/components/PageHeader";
import { formatSessionDate, formatTimestampIst, sourceLabel } from "@/lib/market";
import type { MarketReport } from "@/types";

export const dynamic = "force-dynamic";

const pct = (v: any) =>
  typeof v === "number" ? `${v > 0 ? "+" : ""}${v.toFixed(2)}%` : "—";

export default async function ReportsPage() {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  let reports: any[] = [];
  try {
    const res = await fetch(`${base}/api/reports?limit=15`);
    reports = (await res.json()).reports || [];
  } catch {
    /* backend optional in dev */
  }

  return (
    <main className="page">
      <PageHeader
        eyebrow="Research"
        title="AI market reports"
        description="Automated market-intelligence reports generated hourly during market hours and daily at close."
      >
        <span className="pill pill-accent">{reports.length} reports</span>
        <span className="pill pill-flat">Rule engine</span>
      </PageHeader>

      {reports.length ? (
        <div className="flex flex-col gap-4">
          {reports.map((r: MarketReport) => {
            const content = r.content || {};
            return (
              <section key={r.id} className="glass-card card-hover p-5 sm:p-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="pill pill-accent">{String(r.report_type || "market").toUpperCase()}</span>
                    <span className="chip !py-0.5">
                      {Array.from(new Set((content.market_sources || []).map(sourceLabel))).join(" · ") || "Official EOD"}
                    </span>
                    <span className="text-[11px] text-fg-dim" suppressHydrationWarning>
                      {r.generated_at ? new Date(r.generated_at).toLocaleString("en-IN") : "—"}
                    </span>
                    <span className="text-[11px] text-fg-dim">
                      Session {formatSessionDate(content.market_session)} · Fetched {formatTimestampIst(content.fetched_at)}
                    </span>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-fg-dim">
                    Report #{r.id}
                  </span>
                </div>

                <h2 className="mt-3 text-xl font-bold tracking-tight text-ink">
                  {content.report_type || r.report_type || "Market"} report
                </h2>
                <p className="mt-2 max-w-4xl text-sm leading-relaxed text-fg-muted">
                  {content.market_summary || "No summary available for this report."}
                </p>

                <div className="mt-5 grid gap-4 md:grid-cols-3">
                  <div className="rounded-2xl border border-line/60 bg-white/45 p-4">
                    <h3 className="text-[10px] font-bold uppercase tracking-[0.14em] text-fg-dim">
                      Index movements
                    </h3>
                    <ul className="mt-2.5 space-y-1.5">
                      {(content.index_movements || []).slice(0, 5).map((m: any, i: number) => (
                        <li key={i} className="flex items-center justify-between gap-2 text-xs">
                          <span className="font-medium text-fg">{m.symbol || "—"}</span>
                          <span
                            className={`pill !px-2 !py-0.5 !text-[10px] ${
                              typeof m.change_pct === "number" && m.change_pct > 0
                                ? "pill-up"
                                : typeof m.change_pct === "number" && m.change_pct < 0
                                  ? "pill-down"
                                  : "pill-flat"
                            }`}
                          >
                            {pct(m.change_pct)}
                          </span>
                        </li>
                      ))}
                      {!(content.index_movements || []).length && (
                        <li className="text-xs text-fg-muted">No index data.</li>
                      )}
                    </ul>
                  </div>

                  <div className="rounded-2xl border border-line/60 bg-white/45 p-4">
                    <h3 className="text-[10px] font-bold uppercase tracking-[0.14em] text-fg-dim">
                      Top performers
                    </h3>
                    <ul className="mt-2.5 space-y-1.5">
                      {(content.top_performers || []).slice(0, 5).map((m: any, i: number) => (
                        <li key={i} className="flex items-center justify-between gap-2 text-xs">
                          <span className="font-medium text-fg">{m.symbol || "—"}</span>
                          <span className="pill pill-up !px-2 !py-0.5 !text-[10px]">{pct(m.change_pct)}</span>
                        </li>
                      ))}
                      {!(content.top_performers || []).length && (
                        <li className="text-xs text-fg-muted">No data.</li>
                      )}
                    </ul>

                    <h3 className="mt-4 text-[10px] font-bold uppercase tracking-[0.14em] text-fg-dim">
                      Top losers
                    </h3>
                    <ul className="mt-2.5 space-y-1.5">
                      {(content.top_losers || []).slice(0, 5).map((m: any, i: number) => (
                        <li key={i} className="flex items-center justify-between gap-2 text-xs">
                          <span className="font-medium text-fg">{m.symbol || "—"}</span>
                          <span className="pill pill-down !px-2 !py-0.5 !text-[10px]">{pct(m.change_pct)}</span>
                        </li>
                      ))}
                      {!(content.top_losers || []).length && (
                        <li className="text-xs text-fg-muted">No data.</li>
                      )}
                    </ul>
                  </div>

                  <div className="rounded-2xl border border-line/60 bg-white/45 p-4">
                    <h3 className="text-[10px] font-bold uppercase tracking-[0.14em] text-fg-dim">
                      AI signals
                    </h3>
                    <ul className="mt-2.5 space-y-1.5">
                      {(content.ai_signals_top || []).slice(0, 6).map((s: any, i: number) => (
                        <li key={i} className="flex items-center justify-between gap-2 text-xs">
                          <span className="font-medium text-fg">{s.symbol || "—"}</span>
                          <span
                            className={`pill !px-2 !py-0.5 !text-[10px] ${
                              s.signal_type === "BUY"
                                ? "pill-up"
                                : s.signal_type === "SELL"
                                  ? "pill-down"
                                  : "pill-flat"
                            }`}
                          >
                            {s.signal_type || "HOLD"}
                          </span>
                        </li>
                      ))}
                      {!(content.ai_signals_top || []).length && (
                        <li className="text-xs text-fg-muted">No signals in this report.</li>
                      )}
                    </ul>
                  </div>
                </div>

                {(content.latest_news || []).length ? (
                  <div className="mt-5">
                    <h3 className="text-[10px] font-bold uppercase tracking-[0.14em] text-fg-dim">
                      Latest news
                    </h3>
                    <ul className="mt-2 space-y-1.5">
                      {(content.latest_news || []).slice(0, 8).map((n: any, i: number) => (
                        <li key={i} className="flex gap-2 text-xs leading-relaxed text-fg-muted">
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden />
                          {n.title}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </section>
            );
          })}
        </div>
      ) : (
        <section className="glass-card card-pad">
          <div className="rounded-2xl border border-dashed border-line bg-white/40 px-6 py-16 text-center">
            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent">
              <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                <path d="M7 3.5h7l4 4V19a1.5 1.5 0 01-1.5 1.5h-9A1.5 1.5 0 016 19V5A1.5 1.5 0 017.5 3.5z" />
                <path d="M14 3.5V8h4" />
              </svg>
            </span>
            <p className="mt-3 text-sm font-semibold text-ink">No reports yet</p>
            <p className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-fg-muted">
              Reports are generated during market hours and at close. They will appear here automatically once
              the report engine has run.
            </p>
          </div>
        </section>
      )}
    </main>
  );
}
