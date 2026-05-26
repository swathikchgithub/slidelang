"use client";

import { Editor } from "@monaco-editor/react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { compileUrl, fetchDeck, updateDeck } from "@/lib/api";

export default function DeckPage() {
  const params = useParams<{ id: string }>();
  const deckId = params.id;

  const [jsonText, setJsonText] = useState<string>("");
  const [iframeUrl, setIframeUrl] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const [timing, setTiming] = useState<{
    generationMs: number;
    repaired: boolean;
    attempts: number;
    warnings: number;
  } | null>(null);


  useEffect(() => {
    setLoading(true);
    fetchDeck(deckId)
      .then((res) => {
        setJsonText(JSON.stringify(res.deck, null, 2));
        setIframeUrl(compileUrl(deckId));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));

    // Read timing data stashed by the landing page, then clean it up.
    const key = `slidelang:timing:${deckId}`;
    const stashed = sessionStorage.getItem(key);
    if (stashed) {
      try {
        setTiming(JSON.parse(stashed));
      } catch {
        /* ignore malformed data */
      }
      sessionStorage.removeItem(key);
    }
  }, [deckId]);

  const onChange = useCallback(
    (value: string | undefined) => {
      if (value === undefined) return;
      setJsonText(value);
      setError(null);

      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(async () => {
        let parsed: unknown;
        try {
          parsed = JSON.parse(value);
        } catch (e: unknown) {
          const msg = e instanceof Error ? e.message : String(e);
          setError(`JSON syntax error: ${msg}`);
          return;
        }
        try {
          setSaving(true);
          await updateDeck(deckId, parsed as Record<string, unknown>);
          setIframeUrl(compileUrl(deckId));
        } catch (e: unknown) {
          setError(e instanceof Error ? e.message : String(e));
        } finally {
          setSaving(false);
        }
      }, 600);
    },
    [deckId],
  );

  return (
    <main className="h-screen flex flex-col">
      <header className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-950">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-sm text-zinc-400 hover:text-white">← New deck</Link>
          <span className="text-xs text-zinc-500">deck: {deckId}</span>
          {timing && (
            <span className="text-xs text-emerald-400 font-mono" title={`${timing.attempts} attempt(s), ${timing.warnings} warning(s)`}>
              ⚡ {(timing.generationMs / 1000).toFixed(1)}s
              {timing.repaired && <span className="ml-1 text-amber-400">repaired</span>}
            </span>
          )}
          {saving && <span className="text-xs text-zinc-500">saving…</span>}
        </div>
        <Link
          href={`/deck/${deckId}/present`}
          className="px-3 py-1.5 rounded bg-white text-black text-sm font-medium hover:bg-zinc-200"
        >
          Present
        </Link>
      </header>

      {error && (
        <div className="px-4 py-2 bg-red-950 border-b border-red-900 text-red-200 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-zinc-500 text-sm">
          Loading deck…
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-2 min-h-0">
          <div className="border-r border-zinc-800 min-h-0">
            <Editor
              height="100%"
              defaultLanguage="json"
              theme="vs-dark"
              value={jsonText}
              onChange={onChange}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                tabSize: 2,
                wordWrap: "on",
                scrollBeyondLastLine: false,
              }}
            />
          </div>
          <div className="bg-black min-h-0">
            {iframeUrl && (
              <iframe
                key={iframeUrl}
                src={iframeUrl}
                className="w-full h-full border-0"
                title="deck preview"
              />
            )}
          </div>
        </div>
      )}
    </main>
  );
}
