"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const f = (v: any) =>
  typeof v === "number" ? v.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "—";

const money = (v: any) => (typeof v === "number" ? `₹${f(v)}` : "—");

export default function PaperTradingPanel({ wallet: initialWallet }: { wallet: any }) {
  const [wallet, setWallet] = useState(initialWallet || {});
  const [form, setForm] = useState({ symbol: "", action: "BUY", qty: "1", entry: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [trades, setTrades] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);

  const reload = async () => {
    try {
      setWallet(await api.get("/api/paper/wallet"));
      setTrades((await api.get("/api/paper/trades")).trades || []);
    } catch {
      /* keep current state */
    }
  };

  useEffect(() => {
    reload();
    const t = setInterval(reload, 60_000);
    return () => clearInterval(t);
  }, []);

  const place = async () => {
    setMsg(null);
    setErr(null);
    setBusy(true);
    try {
      const r = await api.post<any>("/api/paper/order", {
        symbol: form.symbol,
        action: form.action,
        qty: Number(form.qty),
        entry_price: form.entry ? Number(form.entry) : null,
      });
      setMsg(
        `${r.action} ${r.qty}×${r.symbol} @ ₹${f(r.price)} — wallet ${money(r.wallet_balance)}`
      );
      setForm({ ...form, qty: "1", entry: "" });
      await reload();
    } catch (e: any) {
      setErr(e?.message || "Order failed.");
    } finally {
      setBusy(false);
    }
  };

  const totalPnl = typeof wallet.total_pnl === "number" ? wallet.total_pnl : null;
  const openPnl = typeof wallet.open_positions_pnl === "number" ? wallet.open_positions_pnl : null;

  const stats: { label: string; value: string; tone?: string; hint?: string }[] = [
    { label: "Wallet balance", value: money(wallet.wallet_balance), hint: "Available cash" },
    { label: "Initial balance", value: money(wallet.initial_balance), hint: "Starting capital" },
    {
      label: "Open positions PnL",
      value: money(openPnl),
      tone: openPnl == null ? "text-ink" : openPnl >= 0 ? "text-up" : "text-down",
      hint: "Unrealised",
    },
    {
      label: "Total PnL",
      value: money(totalPnl),
      tone: totalPnl == null ? "text-ink" : totalPnl >= 0 ? "text-up" : "text-down",
      hint: "Realised + unrealised",
    },
    { label: "Total trades", value: String(wallet.total_trades ?? 0), hint: "Simulated orders" },
  ];

  return (
    <div className="flex flex-col gap-5">
      <section>
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="card-title">Virtual wallet</h2>
            <p className="card-sub">Simulated capital — no real money involved</p>
          </div>
          <span className="pill pill-accent">Paper mode</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {stats.map((s, i) => (
            <div
              key={s.label}
              className={`${
                i === 0
                  ? "relative overflow-hidden rounded-2xl border border-transparent bg-emerald-cta p-4 text-white shadow-emerald"
                  : "glass-card card-hover p-4"
              }`}
            >
              {i === 0 && (
                <span aria-hidden className="pointer-events-none absolute -right-6 -top-8 h-24 w-24 rounded-full bg-white/10 blur-2xl" />
              )}
              <p className={i === 0 ? "text-[10px] font-bold uppercase tracking-[0.12em] text-white/65" : "metric-label"}>
                {s.label}
              </p>
              <p className={`num mt-1.5 text-lg font-extrabold ${i === 0 ? "text-white" : s.tone || "text-ink"}`}>
                {s.value}
              </p>
              {s.hint && (
                <p className={`mt-1 text-[10px] font-medium ${i === 0 ? "text-white/65" : "text-fg-dim"}`}>
                  {s.hint}
                </p>
              )}
            </div>
          ))}
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-3">
        {/* Order form */}
        <section className="glass-card card-pad">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="card-title">Place order</h2>
              <p className="card-sub">Buy or sell at market or a custom entry</p>
            </div>
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent">
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 12h16M13 5l7 7-7 7" />
              </svg>
            </span>
          </div>

          <form
            className="mt-4 grid grid-cols-2 gap-2.5"
            onSubmit={(e) => {
              e.preventDefault();
              place();
            }}
          >
            <label className="col-span-2 block">
              <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-fg-dim">
                Symbol
              </span>
              <input
                value={form.symbol}
                onChange={(e) => setForm({ ...form, symbol: e.target.value })}
                placeholder="e.g. INFY"
                className="field"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-fg-dim">
                Side
              </span>
              <select
                value={form.action}
                onChange={(e) => setForm({ ...form, action: e.target.value })}
                className="field"
              >
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
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
            <label className="col-span-2 block">
              <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-fg-dim">
                Entry price <span className="normal-case tracking-normal text-fg-dim">(optional)</span>
              </span>
              <input
                value={form.entry}
                onChange={(e) => setForm({ ...form, entry: e.target.value })}
                placeholder="Leave blank for market price"
                inputMode="decimal"
                className="field"
              />
            </label>
            <div className="col-span-2 mt-1">
              <button type="submit" disabled={busy} className="btn btn-primary w-full">
                {busy ? "Placing…" : "Place order"}
              </button>
            </div>
          </form>

          {err && <p className="mt-2.5 rounded-lg border border-down/20 bg-down/5 px-3 py-2 text-xs text-down">{err}</p>}
          {msg && <p className="mt-2.5 rounded-lg border border-up/20 bg-up/5 px-3 py-2 text-xs text-up">{msg}</p>}
        </section>

        {/* Open positions */}
        <section className="glass-card card-pad xl:col-span-2">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="card-title">Open positions</h2>
              <p className="card-sub">Live mark-to-market on simulated holdings</p>
            </div>
            <span className="pill pill-flat">{(wallet.positions || []).length}</span>
          </div>

          {(wallet.positions || []).length ? (
            <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
              {(wallet.positions || []).map((p: any) => {
                const pnl = typeof p.unrealised_pnl === "number" ? p.unrealised_pnl : null;
                return (
                  <div key={p.symbol} className="rounded-2xl border border-line/70 bg-white/55 p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-bold text-ink">{p.symbol}</p>
                        <p className="mt-0.5 text-[11px] text-fg-muted">
                          {f(p.qty)} shares · avg ₹{f(p.avg_entry)}
                        </p>
                      </div>
                      <span className={`pill ${pnl == null ? "pill-flat" : pnl >= 0 ? "pill-up" : "pill-down"}`}>
                        {p.unrealised_pct != null
                          ? `${p.unrealised_pct >= 0 ? "+" : ""}${Number(p.unrealised_pct).toFixed(2)}%`
                          : "—"}
                      </span>
                    </div>
                    <p className={`num mt-3 text-lg font-extrabold ${pnl == null ? "text-ink" : pnl >= 0 ? "text-up" : "text-down"}`}>
                      {pnl == null ? "—" : `${pnl >= 0 ? "+" : ""}${money(pnl)}`}
                    </p>
                    <p className="mt-0.5 text-[10px] font-medium text-fg-dim">Unrealised PnL</p>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="mt-4 rounded-xl border border-dashed border-line bg-white/40 px-4 py-12 text-center">
              <p className="text-sm font-semibold text-ink">No open positions</p>
              <p className="mx-auto mt-1 max-w-xs text-xs leading-relaxed text-fg-muted">
                Place a BUY order to open your first simulated position.
              </p>
            </div>
          )}
        </section>
      </div>

      {/* Trade history */}
      <section className="glass-card overflow-hidden">
        <div className="flex items-center justify-between gap-3 border-b border-line/70 px-5 py-4 sm:px-6">
          <div>
            <h2 className="text-sm font-bold text-ink">Trade history</h2>
            <p className="mt-0.5 text-[11px] text-fg-dim">Most recent simulated executions</p>
          </div>
          <span className="pill pill-flat">{trades.length}</span>
        </div>

        {trades.length ? (
          <div className="overflow-x-auto">
            <table className="data-table min-w-[620px]">
              <thead>
                <tr>
                  <th className="pl-5 sm:pl-6">Symbol</th>
                  <th>Side</th>
                  <th className="text-right">Qty</th>
                  <th className="text-right">Price</th>
                  <th className="text-right">PnL</th>
                  <th className="pr-5 text-right sm:pr-6">Executed</th>
                </tr>
              </thead>
              <tbody>
                {trades.slice(0, 20).map((t: any, i: number) => {
                  const pnl = typeof t.pnl === "number" ? t.pnl : null;
                  const buy = String(t.action || "").toUpperCase() === "BUY";
                  return (
                    <tr key={i}>
                      <td className="pl-5 sm:pl-6">
                        <span className="text-sm font-bold text-ink">{t.symbol}</span>
                      </td>
                      <td>
                        <span className={`pill ${buy ? "pill-up" : "pill-down"}`}>{t.action}</span>
                      </td>
                      <td className="num text-right text-sm">{f(t.qty)}</td>
                      <td className="num text-right text-sm">₹{f(t.price)}</td>
                      <td className={`num text-right text-sm font-bold ${pnl == null ? "text-ink" : pnl >= 0 ? "text-up" : "text-down"}`}>
                        {pnl == null ? "—" : `${pnl >= 0 ? "+" : ""}${f(pnl)}`}
                      </td>
                      <td className="pr-5 text-right text-[11px] text-fg-dim sm:pr-6" suppressHydrationWarning>
                        {t.created_at
                          ? new Date(t.created_at).toLocaleString("en-IN", {
                              day: "2-digit",
                              month: "short",
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-5 py-12 text-center text-sm text-fg-muted">No trades yet.</div>
        )}
      </section>
    </div>
  );
}
