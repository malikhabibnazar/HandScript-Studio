"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

export function LivePreview({
  profileId,
  text,
  revision,
  onText,
}: {
  profileId: string;
  text: string;
  revision: number;
  onText: (value: string) => void;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const urlRef = useRef<string | null>(null);
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;

  useEffect(() => {
    return () => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      api.previewDrawing(profileId, text).then((blob) => {
        const next = URL.createObjectURL(blob);
        if (cancelled) {
          URL.revokeObjectURL(next);
          return;
        }
        if (urlRef.current) URL.revokeObjectURL(urlRef.current);
        urlRef.current = next;
        setUrl(next);
        setError("");
      }).catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [profileId, text, revision]);

  return (
    <section className="card">
      <h2>Write your text</h2>
      <p className="sub">The preview places each saved letter on its own. Letters are not joined.</p>
      <textarea value={text} onChange={(event) => onText(event.target.value)} rows={6} />
      <p className="secondary" style={{ marginTop: 8 }}>{words} words</p>
      <h2 style={{ marginTop: 16 }}>Generated output</h2>
      {error ? <p className="secondary">{error}</p> : null}
      {url ? <img className="ruled-preview" src={url} alt="Handwriting preview" /> : <p className="secondary">Building preview…</p>}
    </section>
  );
}
