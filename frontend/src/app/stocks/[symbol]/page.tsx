import { notFound } from "next/navigation";
import StockDetailView from "@/components/StockDetailView";
import type { Analysis, HistoryRow, Meta, Quote, Signal } from "@/types";

async function getJson(url: string): Promise<any> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function fetchData(symbol: string) {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const [detail, analysis, preds, signal] = await Promise.all([
    getJson(`${base}/api/stocks/${symbol}`),
    getJson(`${base}/api/analysis/${symbol}`),
    getJson(`${base}/api/predictions/${symbol}`),
    getJson(`${base}/api/signals/${symbol}`),
  ]);
  if (!detail?.meta) return null;
  return {
    meta: detail.meta as Meta,
    quote: (detail.quote ?? null) as Quote | null,
    history: (detail.history || []) as HistoryRow[],
    analysis: (analysis || {}) as Analysis,
    signal: (signal?.signal || null) as Signal | null,
    predictions: (preds?.predictions || []) as any[],
  };
}

export const dynamic = "force-dynamic";

export default async function StockDetailPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = await params;
  const data = await fetchData(symbol);
  if (!data) notFound();
  return <StockDetailView symbol={data.meta.symbol} {...data} />;
}
