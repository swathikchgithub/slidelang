"use client";

import { useParams } from "next/navigation";
import { compileUrl } from "@/lib/api";

export default function PresentPage() {
  const params = useParams<{ id: string }>();
  const deckId = params.id;
  return (
    <iframe
      src={compileUrl(deckId)}
      className="fixed inset-0 w-screen h-screen border-0"
      title="presentation"
    />
  );
}
