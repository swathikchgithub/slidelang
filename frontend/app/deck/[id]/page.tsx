"use client";

import { Editor } from "@monaco-editor/react";
import type { editor as MonacoEditor } from "monaco-editor";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { compileUrl, fetchDeck, updateDeck } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SlideEntry {
  id: string;
  title?: string;
  layout?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DeckPage() {
  const params = useParams<{ id: string }>();
  const deckId = params.id;

  const [jsonText, setJsonText] = useState<string>("");
  const [iframeUrl, setIframeUrl] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showEditor, setShowEditor] = useState(true);
  const [timing, setTiming] = useState<{
    generationMs: number;
    repaired: boolean;
    attempts: number;
    warnings: number;
  } | null>(null);

  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  const editorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  // ---------------------------------------------------------------------------
  // Initial load
  // ---------------------------------------------------------------------------

  useEffect(() => {
    setLoading(true);
    fetchDeck(deckId)
      .then((res) => {
        setJsonText(JSON.stringify(res.deck, null, 2));
        setIframeUrl(compileUrl(deckId));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));

    const key = `slidelang:timing:${deckId}`;
    const stashed = sessionStorage.getItem(key);
    if (stashed) {
      try { setTiming(JSON.parse(stashed)); } catch { /* ignore */ }
      sessionStorage.removeItem(key);
    }
  }, [deckId]);

  // ---------------------------------------------------------------------------
  // Derived slide list from the editor JSON (best-effort, no throw)
  // ---------------------------------------------------------------------------

  const slides = useMemo<SlideEntry[]>(() => {
    try {
      const parsed = JSON.parse(jsonText);
      return Array.isArray(parsed?.slides) ? parsed.slides : [];
    } catch {
      return [];
    }
  }, [jsonText]);

  // ---------------------------------------------------------------------------
  // Jump Monaco editor to a specific slide by id
  // ---------------------------------------------------------------------------

  const jumpToSlide = useCallback((slideId: string, slideIndex: number) => {
    // 1. Navigate the preview iframe to the clicked slide (cross-origin via postMessage)
    iframeRef.current?.contentWindow?.postMessage(
      { type: "sl-navigate", index: slideIndex },
      "*",
    );

    // 2. Jump Monaco editor cursor to that slide's definition
    const editor = editorRef.current;
    if (!editor) return;
    const model = editor.getModel();
    if (!model) return;
    const text = model.getValue();
    const needle = `"id": "${slideId}"`;
    const idx = text.indexOf(needle);
    if (idx === -1) return;
    const pos = model.getPositionAt(idx);
    editor.revealLineInCenter(pos.lineNumber);
    editor.setPosition(pos);
    editor.focus();
    setShowEditor(true);
  }, []);

  // ---------------------------------------------------------------------------
  // Auto-save on edit (debounced 600ms)
  // ---------------------------------------------------------------------------

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

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <main className="h-screen flex flex-col">
      {/* ---- Header ---- */}
      <header className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-950">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-sm text-zinc-400 hover:text-white">← New deck</Link>
          <span className="text-xs text-zinc-500 font-mono">{deckId}</span>
          {timing && (
            <span
              className="text-xs text-emerald-400 font-mono"
              title={`${timing.attempts} attempt(s), ${timing.warnings} warning(s)`}
            >
              ⚡ {(timing.generationMs / 1000).toFixed(1)}s
              {timing.repaired && <span className="ml-1 text-amber-400">repaired</span>}
            </span>
          )}
          {saving && <span className="text-xs text-zinc-500">saving…</span>}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowEditor((v) => !v)}
            className="px-3 py-1.5 rounded border border-zinc-700 text-zinc-400 text-sm hover:border-zinc-500 hover:text-white transition-colors"
          >
            {showEditor ? "Preview only" : "Show editor"}
          </button>
          <Link
            href={`/deck/${deckId}/present`}
            className="px-3 py-1.5 rounded bg-white text-black text-sm font-medium hover:bg-zinc-200"
          >
            Present
          </Link>
        </div>
      </header>

      {/* ---- Error banner ---- */}
      {error && (
        <div className="px-4 py-2 bg-red-950 border-b border-red-900 text-red-200 text-sm">
          {error}
        </div>
      )}

      {/* ---- Loading state ---- */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center text-zinc-500 text-sm">
          Loading deck…
        </div>
      ) : (
        <div className="flex-1 flex min-h-0">

          {/* ---- Slide list sidebar ---- */}
          <aside className="w-44 flex-shrink-0 border-r border-zinc-800 overflow-y-auto bg-zinc-950">
            <div className="px-2 py-2 text-[10px] uppercase tracking-widest text-zinc-600 font-semibold">
              Slides
            </div>
            {slides.length === 0 ? (
              <p className="px-3 py-2 text-[10px] text-zinc-700">No slides yet</p>
            ) : (
              slides.map((slide, i) => (
                <button
                  key={slide.id}
                  onClick={() => jumpToSlide(slide.id, i)}
                  title={`Jump to slide "${slide.id}" in editor`}
                  className="w-full text-left px-3 py-2 flex items-start gap-2 hover:bg-zinc-800 group transition-colors"
                >
                  <span className="text-[10px] font-mono text-zinc-600 mt-0.5 w-4 flex-shrink-0 text-right">
                    {i + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs text-zinc-300 group-hover:text-white truncate leading-snug">
                      {slide.title || slide.id}
                    </p>
                    <p className="text-[10px] text-zinc-600 truncate">{slide.layout ?? ""}</p>
                  </div>
                </button>
              ))
            )}
          </aside>

          {/* ---- Monaco editor (toggleable) ---- */}
          {showEditor && (
            <div className="flex-1 border-r border-zinc-800 min-h-0 min-w-0">
              <Editor
                height="100%"
                defaultLanguage="json"
                theme="vs-dark"
                value={jsonText}
                onChange={onChange}
                onMount={(editor) => { editorRef.current = editor; }}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  tabSize: 2,
                  wordWrap: "on",
                  scrollBeyondLastLine: false,
                }}
              />
            </div>
          )}

          {/* ---- Preview iframe ---- */}
          <div className="flex-1 bg-black min-h-0 min-w-0">
            {iframeUrl && (
              <iframe
                key={iframeUrl}
                ref={iframeRef}
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
