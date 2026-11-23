import PageHeader from "@/components/PageHeader";
import SearchBar from "@/components/SearchBar";
import StocksTable from "@/components/StocksTable";
import type { StockTableRow } from "@/types";

export const dynamic = "force-dynamic";

async function fetchStocks(): Promise<StockTableRow[]> {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const res = await fetch(`${base}/api/stocks?limit=500`, { cache: "no-store" });
  if (!res.ok) throw new Error("stocks fetch failed");
  return (await res.json()).stocks;
}

export default async function StocksPage() {
  const stocks = await fetchStocks();
  return (
    <main className="page">
      <PageHeader
        eyebrow="Markets"
        title="All listed equities"
        description={`Official NSE & BSE data for ${stocks.length} symbols with latest closing prices, sector classification and index membership.`}
      >
        <span className="pill pill-accent">{stocks.length} tracked</span>
        <span className="pill pill-flat">NSE · BSE</span>
      </PageHeader>

      <div className="mb-4 max-w-xl">
        <SearchBar />
      </div>

      <StocksTable stocks={stocks} />
    </main>
  );
}
