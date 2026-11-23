import PageHeader from "@/components/PageHeader";
import PaperTradingPanel from "@/components/PaperTradingPanel";

export const dynamic = "force-dynamic";

export default async function PaperTradingPage() {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const wallet = await fetch(`${base}/api/paper/wallet`)
    .then((r) => r.json())
    .catch(() => ({}));
  return (
    <main className="page">
      <PageHeader
        eyebrow="Trading"
        title="Paper trading"
        description={`Simulated trading with a virtual wallet${
          wallet.initial_balance != null
            ? ` of ₹${wallet.initial_balance.toLocaleString("en-IN")}`
            : ""
        }. Test ideas with zero real-money risk.`}
      >
        <span className="pill pill-accent">Simulated</span>
        <span className="pill pill-flat">No real money</span>
      </PageHeader>

      <PaperTradingPanel wallet={wallet} />
    </main>
  );
}
