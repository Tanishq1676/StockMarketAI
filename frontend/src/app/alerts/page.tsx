import PageHeader from "@/components/PageHeader";
import AlertsPanel from "@/components/AlertsPanel";

export const dynamic = "force-dynamic";

export default function AlertsPage() {
  return (
    <main className="page">
      <PageHeader
        eyebrow="Trading"
        title="Alerts & notifications"
        description="Configure alerts for price levels, percentage moves, volume spikes and AI signals. Triggered alerts appear as notifications."
      >
        <span className="pill pill-accent">Rule-based</span>
        <span className="pill pill-flat">60s scan</span>
      </PageHeader>

      <AlertsPanel />
    </main>
  );
}
