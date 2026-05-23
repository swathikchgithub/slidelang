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
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchDeck(deckId)
      .then((res) => {
        setJsonText(JSON.stringify(res.deck, null, 2));
        setIframeUrl(compileUrl(deckId));
      })
      .catch((e) => setError(e.message));
  }, [deckId]);

  const onChange = useCallback(
    (value: string | undefined) => {
      if (value === undefined) return;
      setJsonText(value);
      setError(null);

      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(async () => {
        try {
          const parsed = JSON.parse(value);
          setSaving(true);
          await updateDeck(deckId, parsed);
          setIframeUrl(compileUrl(deckId));
        } catch (e: any) {
          setError(e.message);
        } finally {
          setSaving(false);
        }
      }, 600);
    },
    [deckId],
  );

  return (
    <main className="h-screen flex flex-col">
      <header className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-950">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-sm text-zinc-400 hover:text-white">← New deck</Link>
          <span className="text-xs text-zinc-500">deck: {deckId}</span>
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
    </main>
  );
}
