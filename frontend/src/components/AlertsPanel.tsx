"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AlertItem } from "@/types";

const CONDITIONS = [
  "price_above",
  "price_below",
  "pct_up",
  "pct_down",
  "volume_above",
  "volume_below",
  "ai_buy",
  "ai_sell",
];

const LABEL: Record<string, string> = {
  price_above: "Price above",
  price_below: "Price below",
  pct_up: "Gain % above",
  pct_down: "Loss % below",
  volume_above: "Volume above",
  volume_below: "Volume below",
  ai_buy: "AI BUY signal",
  ai_sell: "AI SELL signal",
};

export default function AlertsPanel({ initialAlerts }: { initialAlerts?: AlertItem[] }) {
  const [alerts, setAlerts] = useState<AlertItem[]>(initialAlerts || []);
  const [notifs, setNotifs] = useState<AlertItem[]>([]);
  const [form, setForm] = useState({ symbol: "", condition: "price_above", threshold: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshAll = async () => {
    try {
      const [a, n] = await Promise.all([
        api.get<any>("/api/alerts?active_only=true"),
        api.get<any>("/api/alerts/notifications"),
      ]);
      setAlerts(a.alerts || []);
      setNotifs(n.notifications || []);
      setError(null);
    } catch {
      setError("Unable to reach the alerts service.");
    }
  };

  useEffect(() => {
    refreshAll();
    const t = setInterval(refreshAll, 60_000);
    return () => clearInterval(t);
  }, []);

  const submit = async () => {
    if (!form.symbol || !form.threshold) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/alerts", {
        symbol: form.symbol.toUpperCase(),
        condition: form.condition,
        threshold: Number(form.threshold),
      });
      setForm({ ...form, threshold: "" });
      await refreshAll();
    } catch (e: any) {
      setError(e?.message || "Could not create the alert.");
    } finally {
      setBusy(false);
    }
  };

  const dismiss = async (id: number) => {
    try {
      await api.post(`/api/alerts/${id}/dismiss`);
      await refreshAll();
    } catch {
      setError("Could not dismiss the alert.");
    }
  };

  const remove = async (id: number) => {
    try {
      await api.del(`/api/alerts/${id}`);
      await refreshAll();
    } catch {
      setError("Could not remove the alert.");
    }
  };

  return (
    <section className="glass-card card-pad">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 15.5V11a6 6 0 10-12 0v4.5L4.5 18h15L18 15.5z" />
              <path d="M9.5 21a2.6 2.6 0 005 0" />
            </svg>
          </span>
          <div>
            <h2 className="text-sm font-bold text-ink">Alerts &amp; notifications</h2>
            <p className="mt-0.5 text-[11px] text-fg-dim">
              Price levels, percentage moves, volume spikes and AI signals
            </p>
          </div>
        </div>
        <span className="pill pill-accent">{alerts.length} active</span>
      </div>

      <form
        className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-[1.1fr_1.3fr_1fr_auto]"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <input
          value={form.symbol}
          onChange={(e) => setForm({ ...form, symbol: e.target.value })}
          placeholder="Symbol e.g. RELIANCE"
          aria-label="Alert symbol"
          className="field"
        />
        <select
          value={form.condition}
          onChange={(e) => setForm({ ...form, condition: e.target.value })}
          aria-label="Alert condition"
          className="field"
        >
          {CONDITIONS.map((c) => (
            <option key={c} value={c}>
              {LABEL[c]}
            </option>
          ))}
        </select>
        <input
          value={form.threshold}
          onChange={(e) => setForm({ ...form, threshold: e.target.value })}
          placeholder="Threshold"
          inputMode="decimal"
          aria-label="Alert threshold"
          className="field"
        />
        <button
          type="submit"
          disabled={!form.symbol || !form.threshold || busy}
          className="btn btn-primary h-10 whitespace-nowrap"
        >
          {busy ? "Adding…" : "Add alert"}
        </button>
      </form>

      {error && (
        <p className="mt-3 rounded-lg border border-down/20 bg-down/5 px-3 py-2 text-xs text-down">{error}</p>
      )}

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-fg-dim">Active alerts</p>
          {alerts.length ? (
            <ul className="space-y-2">
              {alerts.map((a) => (
                <li
                  key={a.id}
                  className="flex items-center gap-3 rounded-xl border border-line/70 bg-white/55 px-3 py-2.5"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-[10px] font-extrabold text-accent-dark">
                    {(a.symbol || "—").slice(0, 3)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold text-ink">{a.symbol}</span>
                    <span className="block text-[11px] text-fg-muted">
                      {LABEL[a.condition] || a.condition} ·{" "}
                      <span className="num">
                        {typeof a.threshold === "number" ? a.threshold.toLocaleString("en-IN") : "—"}
                      </span>
                    </span>
                  </span>
                  <span className="flex shrink-0 gap-1">
                    <button
                      type="button"
                      onClick={() => dismiss(a.id)}
                      className="btn btn-ghost btn-xs"
                      title="Dismiss alert"
                    >
                      Dismiss
                    </button>
                    <button
                      type="button"
                      onClick={() => remove(a.id)}
                      className="btn btn-xs border border-down/15 bg-down/5 text-down hover:bg-down/10"
                      title="Remove alert"
                    >
                      Remove
                    </button>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="rounded-xl border border-dashed border-line bg-white/40 px-4 py-8 text-center text-xs text-fg-muted">
              No active alerts. Create one above — notifications appear as conditions are met.
            </div>
          )}
        </div>

        <div>
          <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-fg-dim">
            Recent notifications
          </p>
          {notifs.length ? (
            <ul className="space-y-2">
              {notifs.slice(0, 8).map((a) => (
                <li
                  key={a.id}
                  className="flex items-start gap-2.5 rounded-xl border border-up/20 bg-up/5 px-3 py-2.5"
                >
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-up" aria-hidden />
                  <span className="text-xs leading-relaxed text-fg">
                    {a.message}
                    {a.fired_at && (
                      <span className="mt-0.5 block text-[10px] text-fg-dim" suppressHydrationWarning>
                        {new Date(a.fired_at).toLocaleString("en-IN")}
                      </span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="rounded-xl border border-dashed border-line bg-white/40 px-4 py-8 text-center text-xs text-fg-muted">
              No notifications yet. Fired alerts will be listed here.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
