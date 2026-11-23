const BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      detail = data?.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(`${detail} (${path})`);
  }
  return (await res.json()) as Promise<T>;
}

export const api = {
  get: <T = any,>(path: string) => apiFetch<T>(path),
  post: <T = any,>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T = any,>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  del: <T = any,>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
};

export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || `ws://127.0.0.1:8000/api/ws/market-updates`;
