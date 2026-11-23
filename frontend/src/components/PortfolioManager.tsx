"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { PortfolioSummary, PortfolioStock } from "@/types";

const EMPTY: PortfolioSummary = {
  total_investment: 0,
  current_portfolio_value: 0,
  unrealised_pnl: 0,
  realised_pnl: 0,
  total_pnl: 0,
  total_return_pct: 0,
  stocks: [],
  sector_allocation: {},
};

const fmt = (v: any, digits = 2) =>
  typeof v === "number" ? v.toLocaleString("en-IN", { maximumFractionDigits: digits }) : "—";

const money = (v: any) => (typeof v === "number" ? `₹${fmt(v)}` : "—");

const SECTOR_COLORS = [
  "#0E8A5F",
  "#2FA37A",
  "#6BC3A0",
  "#9DD9BE",
  "#C08A2E",
  "#D14343",
  "#2F7EA8",
  "#8CA096",
];

export default function PortfolioManager({ summary: initial }: { summary: PortfolioSummary }) {
  const [summary, setSummary] = useState<PortfolioSummary>(initial || EMPTY);
  const [form, setForm] = useState({ symbol: "", action: "buy", qty: "1", price: "", fees: "0", taxes: "0" });
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = async () => {
    try {
      setSummary(await api.get<PortfolioSummary>("/api/portfolio/summary"));
    } catch {
      /* keep the current snapshot */
    }
  };

  const submit = async () => {
    setMsg(null);
    setErr(null);
    setBusy(true);
    try {
      await api.post("/api/portfolio/transaction", {
        symbol: form.symbol,
        action: form.action,
        qty: Number(form.qty),
        price: Number(form.price || 0),
        fees: Number(form.fees || 0),
        taxes: Number(form.taxes || 0),
      });
      setForm({ ...form, qty: "1", price: "" });
      setMsg("Transaction recorded.");
      await reload();
    } catch (e: any) {
      setErr(e?.message || "Transaction failed.");
    } finally {
      setBusy(false);
    }
  };

  const pnlTone = (v: any) =>
    typeof v !== "number" ? "text-ink" : v >= 0 ? "text-up" : "text-down";

  const cards: { label: string; value: string; tone?: string; hint?: string }[] = [
    { label: "Total investment", value: money(summary.total_investment) },
    { label: "Current value", value: money(summary.current_portfolio_value), hint: "Mark-to-market" },
    {
      label: "Unrealised PnL",
      value: money(summary.unrealised_pnl),
      tone: pnlTone(summary.unrealised_pnl),
      hint: "Open positions",
    },
    {
      label: "Realised PnL",
      value: money(summary.realised_pnl),
      tone: pnlTone(summary.realised_pnl),
      hint: "Closed positions",
    },
    {
      label: "Total PnL",
      value: money(summary.total_pnl),
      tone: pnlTone(summary.total_pnl),
      hint: "Realised + unrealised",
    },
  ];

  const ret = typeof summary.total_return_pct === "number" ? summary.total_return_pct : null;

  const allocation = Object.entries(summary.sector_allocation || {}).filter(
    ([, v]) => typeof v === "number" && v > 0
  ) as [string, number][];

  let cursor = 0;
  const stops = allocation.map(([key, value], i) => {
    const start = cursor;
    cursor += value;
    return `${SECTOR_COLORS[i % SECTOR_COLORS.length]} ${start}% ${cursor}%`;
  });
  if (cursor < 100) stops.push(`#E9F2EC ${cursor}% 100%`);
  const donut = allocation.length ? `conic-gradient(${stops.join(", ")})` : undefined;

  return (
    <div className="flex flex-col gap-5">
      {/* Summary */}
      <section>
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="card-title">Portfolio summary</h2>
            <p className="card-sub">Automatically calculated from recorded transactions</p>
          </div>
          <span className="pill pill-accent">{summary.stocks?.length || 0} holdings</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
          {cards.map((c) => (
            <div key={c.label} className="glass-card card-hover p-4">
              <p className="metric-label">{c.label}</p>
              <p className={`mt-1.5 num text-lg font-extrabold ${c.tone || "text-ink"}`}>{c.value}</p>
              {c.hint && <p className="mt-1 text-[10px] font-medium text-fg-dim">{c.hint}</p>}
            </div>
          ))}
          <div className="relative overflow-hidden rounded-2xl border border-transparent bg-emerald-cta p-4 text-white shadow-emerald">
            <span aria-hidden className="pointer-events-none absolute -right-6 -top-8 h-24 w-24 rounded-full bg-white/10 blur-2xl" />
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-white/65">Total return</p>
            <p className="num mt-1.5 text-xl font-extrabold">
              {ret != null ? `${ret > 0 ? "+" : ""}${ret.toFixed(2)}%` : "—"}
            </p>
            <p className="mt-1 flex items-center gap-1 text-[10px] font-medium text-white/70">
              <span aria-hidden>{ret == null ? "•" : ret >= 0 ? "▲" : "▼"}</span>
              {ret == null ? "Not available" : ret >= 0 ? "Above invested cost" : "Below invested cost"}
            </p>
          </div>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-5">
        {/* Holdings */}
        <section className="glass-card overflow-hidden xl:col-span-3">
          <div className="flex items-center justify-between gap-3 border-b border-line/70 px-5 py-4 sm:px-6">
            <div>
              <h2 className="text-sm font-bold text-ink">Holdings</h2>
              <p className="mt-0.5 text-[11px] text-fg-dim">Open positions and unrealised performance</p>
            </div>
            <span className="pill pill-flat">{summary.stocks?.length || 0}</span>
          </div>

          {summary.stocks?.length ? (
            <div className="overflow-x-auto">
              <table className="data-table min-w-[720px]">
                <thead>
                  <tr>
                    <th className="pl-5 sm:pl-6">Symbol</th>
                    <th className="text-right">Qty</th>
                    <th className="text-right">Avg buy</th>
                    <th className="text-right">LTP</th>
                    <th className="text-right">Value</th>
                    <th className="text-right">PnL</th>
                    <th className="pr-5 text-right sm:pr-6">Return</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.stocks.map((s: PortfolioStock) => {
                    const pnl = typeof s.unrealised_pnl === "number" ? s.unrealised_pnl : null;
                    const pnlPct = typeof s.unrealised_pct === "number" ? s.unrealised_pct : null;
                    return (
                      <tr key={s.symbol}>
                        <td className="pl-5 sm:pl-6">
                          <div className="flex items-center gap-2.5">
                            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-line/80 bg-white text-[10px] font-extrabold text-accent-dark">
                              {s.symbol.slice(0, 3)}
                            </span>
                            <div>
                              <p className="text-sm font-bold text-ink">{s.symbol}</p>
                              <p className="text-[10px] text-fg-dim">{s.sector || "Equity"}</p>
                            </div>
                          </div>
                        </td>
                        <td className="num text-right text-sm">{fmt(s.qty, 0)}</td>
                        <td className="num text-right text-sm">₹{fmt(s.avg_buy_price)}</td>
                        <td className="num text-right text-sm">₹{fmt(s.current_price)}</td>
                        <td className="num text-right text-sm font-semibold text-ink">₹{fmt(s.current_value)}</td>
                        <td className={`num text-right text-sm font-bold ${pnl == null ? "text-ink" : pnl >= 0 ? "text-up" : "text-down"}`}>
                          {pnl == null ? "—" : `${pnl >= 0 ? "+" : ""}₹${fmt(pnl)}`}
                        </td>
                        <td className="pr-5 text-right sm:pr-6">
                          <span className={`pill ${pnlPct == null ? "pill-flat" : pnlPct >= 0 ? "pill-up" : "pill-down"}`}>
                            {pnlPct == null ? "—" : `${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%`}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-5 py-14 text-center sm:px-6">
              <p className="text-sm font-semibold text-ink">No holdings yet</p>
              <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-fg-muted">
                Record your first buy transaction to start tracking live performance and sector allocation.
              </p>
            </div>
          )}
        </section>

        {/* Form + allocation */}
        <div className="flex flex-col gap-4 xl:col-span-2">
          <section className="glass-card card-pad">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="card-title">Add transaction</h2>
                <p className="card-sub">Record a buy or sell manually</p>
              </div>
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent">
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </span>
            </div>

            <form
              className="mt-4 grid grid-cols-2 gap-2.5"
              onSubmit={(e) => {
                e.preventDefault();
                submit();
              }}
            >
              <label className="col-span-2 block">
                <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-fg-dim">
                  Symbol
                </span>
                <input
                  value={form.symbol}
                  onChange={(e) => setForm({ ...form, symbol: e.target.value })}
                  placeholder="e.g. RELIANCE"
                  className="field"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-fg-dim">
                  Action
                </span>
                <select
                  value={form.action}
                  onChange={(e) => setForm({ ...form, action: e.target.value })}
                  className="field"
                >
                  <option value="buy">Buy</option>
                  <option value="sell">Sell</option>
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-fg-dim">
                  Quantity
                </span>
                <input
                  value={form.qty}
                  onChange={(e) => setForm({ ...form, qty: e.target.value })}
                  placeholder="Qty"
                  inputMode="numeric"
                  className="field"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-fg-dim">
                  Price
                </span>
                <input
                  value={form.price}
                  onChange={(e) => setForm({ ...form, price: e.target.value })}
                  placeholder="₹"
                  inputMode="decimal"
                  className="field"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-fg-dim">
                  Fees
                </span>
                <input
                  value={form.fees}
                  onChange={(e) => setForm({ ...form, fees: e.target.value })}
                  placeholder="0"
                  inputMode="decimal"
                  className="field"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-fg-dim">
                  Taxes
                </span>
                <input
                  value={form.taxes}
                  onChange={(e) => setForm({ ...form, taxes: e.target.value })}
                  placeholder="0"
                  inputMode="decimal"
                  className="field"
                />
              </label>
              <div className="col-span-2 mt-1">
                <button type="submit" disabled={busy} className="btn btn-primary w-full">
                  {busy ? "Recording…" : "Record transaction"}
                </button>
              </div>
            </form>

            {err && <p className="mt-2.5 rounded-lg border border-down/20 bg-down/5 px-3 py-2 text-xs text-down">{err}</p>}
            {msg && <p className="mt-2.5 rounded-lg border border-up/20 bg-up/5 px-3 py-2 text-xs text-up">{msg}</p>}
            <p className="mt-3 text-[10px] leading-relaxed text-fg-dim">
              Calculations are automatic — FIFO sells, transaction costs and mark-to-market valuation.
            </p>
          </section>

          <section className="glass-card card-pad">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="card-title">Sector allocation</h2>
                <p className="card-sub">Exposure by market value</p>
              </div>
              <span className="pill pill-flat">{allocation.length} sectors</span>
            </div>

            {allocation.length ? (
              <div className="mt-4 flex flex-col items-center gap-4 sm:flex-row">
                <div className="relative h-[148px] w-[148px] shrink-0 rounded-full" style={{ background: donut }}>
                  <div className="absolute inset-[18px] flex flex-col items-center justify-center rounded-full bg-white/95 text-center shadow-inner">
                    <span className="num text-lg font-extrabold text-ink">{allocation.length}</span>
                    <span className="text-[9px] font-bold uppercase tracking-[0.14em] text-fg-dim">
                      Sectors
                    </span>
                  </div>
                </div>
                <ul className="w-full space-y-2">
                  {allocation.map(([k, v], i) => (
                    <li key={k} className="flex items-center gap-2">
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-sm"
                        style={{ background: SECTOR_COLORS[i % SECTOR_COLORS.length] }}
                        aria-hidden
                      />
                      <span className="min-w-0 flex-1 truncate text-xs font-medium text-fg-muted">
                        {k || "Other"}
                      </span>
                      <span className="num text-xs font-bold text-ink">{v.toFixed(2)}%</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="mt-4 rounded-xl border border-dashed border-line bg-white/40 px-4 py-8 text-center text-xs text-fg-muted">
                No sector exposure yet.
              </p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
