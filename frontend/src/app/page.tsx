import DashboardPage from "@/components/DashboardPage";

export const dynamic = "force-dynamic";

async function fetchDashboard(): Promise<any> {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const res = await fetch(`${base}/api/dashboard`);
  if (!res.ok) throw new Error("dashboard fetch failed");
  return res.json();
}

export default async function Dashboard() {
  const initial = await fetchDashboard().catch(() => null);
  return <DashboardPage initial={initial} />;
}
