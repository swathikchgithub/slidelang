"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { generateDeck } from "@/lib/api";

const EXAMPLES = [
  "5-slide intro to gradient descent for engineers",
  "Pitch deck for a B2B SaaS that auto-generates technical documentation",
  "8 slides explaining the CAP theorem with a chart of tradeoffs",
];

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function handleSubmit() {
    if (!prompt.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await generateDeck(prompt);
      router.push(`/deck/${res.deck_id}`);
    } catch (e: any) {
      setError(e.message || "generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-2xl">
        <h1 className="text-5xl font-bold tracking-tight mb-2">Slidelang</h1>
        <p className="text-zinc-400 mb-8">Describe a deck. Get editable, presentable slides.</p>

        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. 5-slide intro to vector databases for backend engineers"
          rows={4}
          className="w-full p-4 rounded-lg bg-zinc-900 border border-zinc-800 focus:border-zinc-600 focus:outline-none resize-none text-zinc-100"
          disabled={loading}
        />

        <button
          onClick={handleSubmit}
          disabled={loading || !prompt.trim()}
          className="mt-4 w-full py-3 rounded-lg bg-white text-black font-medium hover:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Generating…" : "Generate deck"}
        </button>

        {error && (
          <div className="mt-4 p-3 rounded bg-red-950 border border-red-900 text-red-200 text-sm">
            {error}
          </div>
        )}

        <div className="mt-10">
          <p className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Try one of these</p>
          <div className="space-y-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => setPrompt(ex)}
                disabled={loading}
                className="block w-full text-left text-sm text-zinc-300 hover:text-white p-3 rounded border border-zinc-800 hover:border-zinc-700"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
