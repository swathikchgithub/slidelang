"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { compileUrl } from "@/lib/api";

export default function PresentPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const deckId = params.id;

  // Keyboard shortcut: press 'q' to quit back to the editor.
  // We avoid Esc because reveal.js uses Esc for its overview mode
  // (inside the iframe). Hijacking it would break that feature.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Ignore if user is typing in an input (unlikely on this page, but safe)
      const target = e.target as HTMLElement;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) {
        return;
      }
      if (e.key === "q" || e.key === "Q") {
        router.push(`/deck/${deckId}`);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [deckId, router]);

  return (
    <>
      <iframe
        src={compileUrl(deckId)}
        className="fixed inset-0 w-screen h-screen border-0"
        title="presentation"
      />
      {/*
        Exit affordance: faint corner button. Opacity is low by default so
        it doesn't compete with slide content during actual presentation.
        On hover it becomes fully visible. Title attribute also shows the
        keyboard shortcut.
      */}
      <Link
        href={`/deck/${deckId}`}
        className="fixed top-3 left-3 z-50 px-3 py-1.5 rounded text-sm
                   bg-black/50 text-white/60 hover:bg-black/80 hover:text-white
                   backdrop-blur-sm transition-opacity opacity-30 hover:opacity-100"
        title="Back to editor (press Q)"
      >
        ← Editor
      </Link>
    </>
  );
}