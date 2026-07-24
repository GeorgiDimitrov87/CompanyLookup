const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export async function createLookup(data: {
  company_name: string;
  location?: string;
  industry?: string;
}) {
  const res = await fetch(`${API_URL}/api/lookups`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create lookup");
  return res.json();
}

export async function getLookup(id: string) {
  const res = await fetch(`${API_URL}/api/lookups/${id}`);
  if (!res.ok) throw new Error("Failed to fetch lookup");
  return res.json();
}

export async function selectCandidate(jobId: string, candidateId: string) {
  const res = await fetch(`${API_URL}/api/lookups/${jobId}/select-candidate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidate_id: candidateId }),
  });
  if (!res.ok) throw new Error("Failed to select candidate");
  return res.json();
}

export async function listLookups() {
  const res = await fetch(`${API_URL}/api/lookups`);
  if (!res.ok) throw new Error("Failed to list lookups");
  return res.json();
}

export function connectWebSocket(
  jobId: string,
  onMessage: (data: Record<string, string>) => void,
): WebSocket {
  const ws = new WebSocket(`${WS_URL}/ws/lookups/${jobId}`);
  ws.onmessage = (event) => onMessage(JSON.parse(event.data));
  return ws;
}
