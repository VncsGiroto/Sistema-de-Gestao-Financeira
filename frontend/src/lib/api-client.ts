const base = (import.meta.env.VITE_API_URL as string) || "/api";

export async function getHealth(): Promise<{ status: string; app: string }> {
  const res = await fetch(`${base}/health`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
