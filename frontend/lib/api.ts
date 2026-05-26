const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface GenerateResponse {
  deck_id: string;
  deck: Record<string, unknown>;
  repaired: boolean;
  attempts: number;
  warnings: Array<{ slide_id: string; code: string; message: string }>;
}

/** Extract the human-readable message from a FastAPI error response body. */
async function extractErrorMessage(res: Response, fallbackPrefix: string): Promise<string> {
  const text = await res.text();
  try {
    const json = JSON.parse(text);
    const detail = json?.detail;
    if (typeof detail === "string") return detail;
    if (typeof detail?.message === "string") return detail.message;
  } catch {
    // not JSON — fall through to raw text
  }
  return `${fallbackPrefix}: ${res.status} ${text}`;
}

export async function generateDeck(prompt: string): Promise<GenerateResponse> {
  const res = await fetch(`${API_URL}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res, "generate failed"));
  }
  return res.json();
}

export async function fetchDeck(deckId: string): Promise<{ deck_id: string; deck: Record<string, unknown> }> {
  const res = await fetch(`${API_URL}/api/decks/${deckId}`);
  if (!res.ok) throw new Error(await extractErrorMessage(res, "fetchDeck failed"));
  return res.json();
}

export async function updateDeck(deckId: string, deck: Record<string, unknown>) {
  const res = await fetch(`${API_URL}/api/decks/${deckId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(deck),
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res, "updateDeck failed"));
  }
  return res.json();
}

export function compileUrl(deckId: string, cacheBuster?: number): string {
  const v = cacheBuster ?? Date.now();
  return `${API_URL}/api/compile/${deckId}?v=${v}`;
}
