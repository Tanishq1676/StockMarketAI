import PageHeader from "@/components/PageHeader";
import PortfolioManager from "@/components/PortfolioManager";
import type { PortfolioSummary } from "@/types";

async function fetchSummary(): Promise<PortfolioSummary> {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const res = await fetch(`${base}/api/portfolio/summary`);
  if (!res.ok) throw new Error("portfolio fetch failed");
  return res.json();
}

export const dynamic = "force-dynamic";

export default async function PortfolioPage() {
  const summary = await fetchSummary();
  return (
    <main className="page">
      <PageHeader
        eyebrow="Trading"
        title="Portfolio management"
        description="Record buys and sells manually — performance, PnL, holdings and sector allocation are calculated automatically."
      >
        <span className="pill pill-accent">Live valuation</span>
        <span className="pill pill-flat">FIFO cost basis</span>
      </PageHeader>

      <PortfolioManager summary={summary} />
    </main>
  );
}
