const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface GenerateResponse {
  deck_id: string;
  deck: Record<string, unknown>;
  repaired: boolean;
  attempts: number;
  warnings: Array<{ slide_id: string; code: string; message: string }>;
}

export async function generateDeck(prompt: string): Promise<GenerateResponse> {
  const res = await fetch(`${API_URL}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`generate failed: ${res.status} ${body}`);
  }
  return res.json();
}

export async function fetchDeck(deckId: string): Promise<{ deck_id: string; deck: Record<string, unknown> }> {
  const res = await fetch(`${API_URL}/api/decks/${deckId}`);
  if (!res.ok) throw new Error(`fetchDeck failed: ${res.status}`);
  return res.json();
}

export async function updateDeck(deckId: string, deck: Record<string, unknown>) {
  const res = await fetch(`${API_URL}/api/decks/${deckId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(deck),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`updateDeck failed: ${res.status} ${body}`);
  }
  return res.json();
}

export function compileUrl(deckId: string, cacheBuster?: number): string {
  const v = cacheBuster ?? Date.now();
  return `${API_URL}/api/compile/${deckId}?v=${v}`;
}
