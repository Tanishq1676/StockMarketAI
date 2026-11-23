/** Market-data provenance helpers.
 *
 * The backend stores timestamps as naive UTC and session dates as
 * ``YYYY-MM-DD``.  Everything shown to a user is rendered in IST so the
 * trading session and the ingest time can never be confused.
 */

export type DataMode = "live" | "delayed" | "close" | "unavailable";

type Provenance = {
  data_source?: string | null;
  is_live?: boolean | null;
  delay_minutes?: number | null;
};

const SOURCE_LABELS: Record<string, string> = {
  nse: "NSE official",
  bse: "BSE official",
  "nse-index": "NSE official",
  "bse-index": "BSE official",
  "nse-live": "NSE live",
  demo: "Synthetic demo",
  provider: "Third-party feed",
  unavailable: "Unavailable",
};

export function sourceLabel(source?: string | null): string {
  if (!source) return "Market data";
  return SOURCE_LABELS[source] || source;
}

export function dataMode(row?: Provenance | null): DataMode {
  if (!row || !row.data_source || row.data_source === "unavailable") return "unavailable";
  if (row.data_source === "demo") return "unavailable";
  if (row.is_live) return "live";
  if (typeof row.delay_minutes === "number" && row.delay_minutes > 0) return "delayed";
  return "close";
}

export const DATA_MODE_LABEL: Record<DataMode, string> = {
  live: "Live",
  delayed: "Delayed",
  close: "Latest close",
  unavailable: "No verified data",
};

export const DATA_MODE_HINT: Record<DataMode, string> = {
  live: "Streaming from the exchange during market hours",
  delayed: "Exchange feed delayed by a few minutes",
  close: "Verified end-of-day closing price from the last session",
  unavailable: "No official NSE/BSE price is stored for this symbol",
};

/** Parse a backend timestamp.  Naive values are UTC by contract. */
export function parseTimestamp(value?: string | null): Date | null {
  if (!value) return null;
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(value);
  const parsed = new Date(hasZone ? value : `${value}Z`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/** "21 Nov 2026, 2:06 pm IST" */
export function formatTimestampIst(value?: string | null): string {
  const date = parseTimestamp(value);
  if (!date) return "—";
  return `${date.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  })} IST`;
}

/** "Fri, 20 Nov 2026" for a session date (no time-zone shift). */
export function formatSessionDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(`${value}T00:00:00+05:30`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", {
    timeZone: "Asia/Kolkata",
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/** Short session label, e.g. "20 Nov 2026". */
export function formatSessionShort(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(`${value}T00:00:00+05:30`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/** "Fri, 20 Nov 2026 · latest close" */
export function sessionLine(
  row?: (Provenance & { trade_date?: string | null }) | null
): string {
  if (!row?.trade_date) return "Session date unavailable";
  return `${formatSessionDate(row.trade_date)} · ${DATA_MODE_LABEL[dataMode(row)].toLowerCase()}`;
}
