"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { generateDeck } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Example prompts organised by category
// ---------------------------------------------------------------------------

const CATEGORIES = [
  {
    label: "Visual Stories",
    icon: "🖼️",
    examples: [
      "Iconic concert stages around the world — 6 slides each with a full photo and venue description on the side",
      "Marvel Cinematic Universe heroes — 6 slides each with a photo and short character bio on the side",
      "AI-imagined future technologies — 5 full-bleed photo slides with a one-line caption",
      "7 stunning national parks around the world with a landscape photo and description on each slide",
      "Endangered animals — 5 slides each with a wildlife photo and conservation status on the side",
      "Street food from 6 countries — one photo and description per slide",
    ],
  },
  {
    label: "Engineering",
    icon: "⚙️",
    examples: [
      "5-slide intro to gradient descent for engineers",
      "Explain transformer self-attention in 6 slides",
      "System design: URL shortener — 7 slides",
      "Rust ownership and borrowing in 5 slides",
    ],
  },
  {
    label: "Data & AI",
    icon: "🧠",
    examples: [
      "8 slides on the CAP theorem with a tradeoff chart",
      "Fine-tuning vs RAG — when to use each: 6 slides",
      "Intro to vector databases for backend engineers",
    ],
  },
  {
    label: "Business",
    icon: "📈",
    examples: [
      "Pitch deck for a B2B SaaS that auto-generates docs",
      "OKR planning workshop — 5 slides",
      "Go-to-market strategy framework in 6 slides",
    ],
  },
  {
    label: "Science",
    icon: "🔬",
    examples: [
      "Quantum entanglement for a general audience — 5 slides",
      "How CRISPR gene editing works — 6 slides",
      "Climate change: data and projections — 7 slides",
    ],
  },
];

// ---------------------------------------------------------------------------
// MRU (most recently used) decks — persisted to localStorage
// ---------------------------------------------------------------------------

interface RecentDeck {
  deck_id: string;
  title: string;
  created_at: number;
}

const RECENT_KEY = "slidelang:recent";
const RECENT_MAX = 5;

function loadRecent(): RecentDeck[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function saveRecent(deck_id: string, title: string) {
  const next: RecentDeck[] = [
    { deck_id, title, created_at: Date.now() },
    ...loadRecent().filter((d) => d.deck_id !== deck_id),
  ].slice(0, RECENT_MAX);
  localStorage.setItem(RECENT_KEY, JSON.stringify(next));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [recent, setRecent] = useState<RecentDeck[]>([]);
  const startRef = useRef<number>(0);
  const tickRef = useRef<NodeJS.Timeout | null>(null);
  const router = useRouter();

  // Load recent decks, then probe each one and prune any that no longer exist
  useEffect(() => {
    const stored = loadRecent();
    if (stored.length === 0) return;

    // Show immediately so the page doesn't flash
    setRecent(stored);

    // Probe all decks in parallel — remove 404s from display + localStorage
    Promise.all(
      stored.map(async (d) => {
        try {
          const res = await fetch(`${API_URL}/api/decks/${d.deck_id}`);
          return res.ok ? d : null;
        } catch {
          // Network error (server down) — keep the entry, don't prune
          return d;
        }
      }),
    ).then((results) => {
      const valid = results.filter(Boolean) as RecentDeck[];
      if (valid.length !== stored.length) {
        localStorage.setItem(RECENT_KEY, JSON.stringify(valid));
        setRecent(valid);
      }
    });
  }, []);

  // Elapsed-time ticker while loading
  useEffect(() => {
    if (loading) {
      startRef.current = Date.now();
      setElapsed(0);
      tickRef.current = setInterval(() => {
        setElapsed((Date.now() - startRef.current) / 1000);
      }, 100);
    } else if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, [loading]);

  async function handleSubmit() {
    if (!prompt.trim() || loading) return;
    setLoading(true);
    setError(null);
    const t0 = Date.now();
    try {
      const res = await generateDeck(prompt);
      const elapsedMs = Date.now() - t0;

      // Stash timing for the editor page
      sessionStorage.setItem(
        `slidelang:timing:${res.deck_id}`,
        JSON.stringify({
          generationMs: elapsedMs,
          repaired: res.repaired,
          attempts: res.attempts,
          warnings: res.warnings.length,
        }),
      );

      // Persist to MRU
      const title =
        (res.deck as any)?.meta?.title ?? prompt.slice(0, 60);
      saveRecent(res.deck_id, title);
      setRecent(loadRecent());

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
        {/* Title */}
        <h1 className="text-5xl font-bold tracking-tight mb-2">Slidelang</h1>
        <p className="text-zinc-400 mb-8">Describe a deck. Get editable, presentable slides.</p>

        {/* Prompt input */}
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
          }}
          placeholder="e.g. 5-slide intro to vector databases for backend engineers"
          rows={4}
          className="w-full p-4 rounded-lg bg-zinc-900 border border-zinc-800 focus:border-zinc-600 focus:outline-none resize-none text-zinc-100"
          disabled={loading}
        />

        {/* Generate button */}
        <button
          onClick={handleSubmit}
          disabled={loading || !prompt.trim()}
          className={`mt-4 w-full py-3 rounded-lg font-medium transition-all duration-200 ${
            loading
              ? "bg-zinc-800 border border-zinc-600 text-zinc-400 cursor-wait"
              : "bg-white text-black hover:bg-zinc-200 disabled:opacity-40 disabled:cursor-not-allowed"
          }`}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-zinc-600 border-t-zinc-300 rounded-full animate-spin" />
              Generating… {elapsed.toFixed(1)}s
            </span>
          ) : (
            "Generate deck"
          )}
        </button>
        <p className="mt-1.5 text-center text-zinc-600 text-xs">⌘ + Enter to generate</p>

        {/* Error */}
        {error && (
          <div className="mt-4 p-3 rounded bg-red-950 border border-red-900 text-red-200 text-sm">
            {error}
          </div>
        )}

        {/* Recent decks */}
        {recent.length > 0 && (
          <section className="mt-10">
            <p className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Recent decks</p>
            <div className="flex flex-wrap gap-2">
              {recent.map((d) => (
                <Link
                  key={d.deck_id}
                  href={`/deck/${d.deck_id}`}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-zinc-800 bg-zinc-900 text-zinc-300 text-sm hover:border-zinc-600 hover:text-white transition-colors"
                >
                  <span className="text-zinc-500 text-xs font-mono">{d.deck_id}</span>
                  <span className="text-zinc-600">·</span>
                  <span className="truncate max-w-[200px]">{d.title}</span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Categorised examples */}
        <section className="mt-10 space-y-6">
          <p className="text-xs uppercase tracking-wider text-zinc-500">Try one of these</p>
          {CATEGORIES.map((cat) => (
            <div key={cat.label}>
              <p className="text-xs text-zinc-500 mb-2 flex items-center gap-1.5">
                <span>{cat.icon}</span>
                <span className="uppercase tracking-wider">{cat.label}</span>
              </p>
              <div className="flex flex-wrap gap-2">
                {cat.examples.map((ex) => (
                  <button
                    key={ex}
                    onClick={() => setPrompt(ex)}
                    disabled={loading}
                    className="px-3 py-1.5 rounded-full border border-zinc-800 bg-zinc-900/50 text-zinc-400 text-sm hover:border-zinc-600 hover:text-zinc-200 hover:bg-zinc-800 transition-all disabled:opacity-40"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </section>
      </div>
    </main>
  );
}
