import Link from "next/link";
import type { StockTableRow } from "@/types";
import {
  DATA_MODE_LABEL,
  dataMode,
  formatSessionShort,
} from "@/lib/market";

const fmt = (v: any) =>
  typeof v === "number" ? v.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "—";

export default function StocksTable({ stocks }: { stocks: StockTableRow[] }) {
  const advancing = stocks.filter((s) => (s.change_pct ?? 0) > 0).length;
  const declining = stocks.filter((s) => (s.change_pct ?? 0) < 0).length;

  return (
    <section className="glass-card overflow-hidden">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line/70 px-5 py-4 sm:px-6">
        <div>
          <h2 className="text-sm font-bold text-ink">All listed equities</h2>
          <p className="mt-0.5 text-[11px] text-fg-dim">
            {stocks.length} tracked · NSE &amp; BSE universe
          </p>
        </div>
        <div className="flex items-center gap-2 text-[11px]">
          <span className="pill pill-up">▲ {advancing} advancing</span>
          <span className="pill pill-down">▼ {declining} declining</span>
        </div>
      </div>

      {stocks.length ? (
        <div className="overflow-x-auto">
          <table className="data-table min-w-[960px]">
            <thead>
              <tr>
                <th className="pl-5 sm:pl-6">Company</th>
                <th>Exchange</th>
                <th>Sector</th>
                <th>Market cap</th>
                <th className="text-right">Price</th>
                <th className="text-right">As of</th>
                <th className="pr-5 text-right sm:pr-6">Change</th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((s) => {
                const change = typeof s.change_pct === "number" ? s.change_pct : null;
                const up = change != null && change > 0;
                const down = change != null && change < 0;
                return (
                  <tr key={s.symbol} className="group">
                    <td className="pl-5 sm:pl-6">
                      <Link href={`/stocks/${s.symbol}`} className="flex items-center gap-3">
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line/80 bg-white text-[10px] font-extrabold text-accent-dark">
                          {s.symbol.slice(0, 3)}
                        </span>
                        <span className="min-w-0">
                          <span className="block text-sm font-bold text-ink transition-colors group-hover:text-accent-dark">
                            {s.symbol}
                          </span>
                          <span className="block max-w-[220px] truncate text-[11px] text-fg-muted">
                            {s.name}
                          </span>
                        </span>
                      </Link>
                    </td>
                    <td>
                      <span className="chip !py-0.5">{s.exchange}</span>
                    </td>
                    <td className="text-xs text-fg-muted">{s.sector || "—"}</td>
                    <td>
                      <span className="pill pill-flat !px-2 !py-0.5 !text-[10px] capitalize">
                        {s.market_cap || "—"}
                      </span>
                    </td>
                    <td className="num text-right text-sm font-semibold text-ink">₹{fmt(s.price)}</td>
                    <td className="text-right">
                      <span className="block text-[11px] font-semibold text-fg-muted">
                        {s.trade_date ? formatSessionShort(s.trade_date) : "—"}
                      </span>
                      <span className="block text-[10px] text-fg-dim">
                        {s.data_source ? DATA_MODE_LABEL[dataMode(s)] : "No data"}
                      </span>
                    </td>
                    <td className="pr-5 text-right sm:pr-6">
                      <span className={`pill ${up ? "pill-up" : down ? "pill-down" : "pill-flat"}`}>
                        {up ? "▲" : down ? "▼" : "•"}{" "}
                        {change != null ? `${change > 0 ? "+" : ""}${change.toFixed(2)}%` : "—"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="px-5 py-16 text-center text-sm text-fg-muted">No equities available.</div>
      )}
    </section>
  );
}
