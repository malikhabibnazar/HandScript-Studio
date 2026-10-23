"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge, useConfirm, useToast } from "@/components/ui";
import { API_URL, api } from "@/lib/api";
import type { HandfontedGlyph, Profile } from "@/lib/types";

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
const ALPHABET_CHARS = new Set(ALPHABET);

function labelsInSample(rows: HandfontedGlyph[]) {
  return new Set(rows.map((glyph) => glyph.label).filter((label) => label.length === 1 && ALPHABET_CHARS.has(label)));
}

export function HandfontedStudio({
  profile,
  onProfile,
}: {
  profile: Profile;
  onProfile: (profile: Profile) => void;
}) {
  const router = useRouter();
  const toast = useToast();
  const { confirm, dialog } = useConfirm();
  const [name, setName] = useState(profile.name);
  const [thickness, setThickness] = useState(profile.style?.thickness ?? 100);
  const [glyphs, setGlyphs] = useState<HandfontedGlyph[]>(profile.style?.glyphs ?? []);
  const [busy, setBusy] = useState<"process" | "font" | "preview" | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [revisions, setRevisions] = useState<Record<string, number>>({});
  const [preview, setPreview] = useState<string | null>(null);
  const [sample, setSample] = useState(profile.preview_text || "The quick brown fox 0123456789");
  const lock = useRef(false);
  const writes = useRef(Promise.resolve());

  function enqueue<T>(task: () => Promise<T>): Promise<T> {
    const run = writes.current.then(task, task);
    writes.current = run.then(() => undefined, () => undefined);
    return run;
  }

  useEffect(() => {
    setName(profile.name);
    setThickness(profile.style?.thickness ?? 100);
    setGlyphs(profile.style?.glyphs ?? []);
    setSample(profile.preview_text || "The quick brown fox 0123456789");
  }, [profile.id, profile.style?.font_path]);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview);
  }, [preview]);

  const sets = useMemo(() => {
    const grouped = new Map<number, HandfontedGlyph[]>();
    for (const glyph of glyphs) {
      const number = glyph.sample ?? 1;
      grouped.set(number, [...(grouped.get(number) ?? []), glyph]);
    }
    return [...grouped.entries()].sort((left, right) => left[0] - right[0]);
  }, [glyphs]);

  const kept = glyphs.filter((glyph) => glyph.kept && glyph.label.length === 1);
  const locked = busy !== null || pending !== null;

  function replace(id: string, patch: Partial<HandfontedGlyph>) {
    const next = glyphs.map((glyph) => (glyph.id === id ? { ...glyph, ...patch } : glyph));
    setGlyphs(next);
    return next;
  }

  async function saveGlyphs(next: HandfontedGlyph[], nextThickness = thickness) {
    const saved = await api.saveHandfontedGlyphs(profile.id, next, nextThickness);
    onProfile(saved);
  }

  async function showPreview(text: string) {
    const blob = await api.previewHandfonted(profile.id, text);
    setPreview((current) => {
      if (current) URL.revokeObjectURL(current);
      return URL.createObjectURL(blob);
    });
  }

  async function readPhoto(file: File) {
    if (lock.current) return;
    lock.current = true;
    setBusy("process");
    try {
      await enqueue(async () => {
        if (name.trim() && name.trim() !== profile.name) {
          await api.updateProfile(profile.id, { name: name.trim() });
        }
        const next = await api.processHandfonted(profile.id, file);
        onProfile(next);
        setGlyphs(next.style?.glyphs ?? []);
        setPreview(null);
        const added = (next.style?.glyphs ?? []).filter((glyph) => (glyph.sample ?? 1) === sets.length + 1).length
          || (next.style?.glyphs.length ?? 0);
        toast(`${added} characters found`, "success");
      });
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not read the photo", "danger");
    } finally {
      lock.current = false;
      setBusy(null);
    }
  }

  async function uploadCharacter(file: File, target: { glyphId: string } | { label: string; sample: number }) {
    if (lock.current) return;
    if (file.type && !file.type.startsWith("image/")) {
      toast("Upload an image of one character.", "danger");
      return;
    }
    const glyphId = "glyphId" in target ? target.glyphId : "";
    const key = "glyphId" in target ? target.glyphId : `${target.sample}:${target.label}`;
    const label = "label" in target ? target.label : "";
    const sampleNo = "sample" in target ? target.sample : 0;
    lock.current = true;
    setPending(key);
    try {
      await enqueue(async () => {
        await saveGlyphs(glyphs);
        const next = glyphId
          ? await api.replaceHandfontedGlyph(profile.id, glyphId, file)
          : await api.addHandfontedGlyph(profile.id, file, label, sampleNo);
        onProfile(next);
        setGlyphs(next.style?.glyphs ?? []);
        if (glyphId) {
          setRevisions((current) => ({ ...current, [glyphId]: (current[glyphId] ?? 0) + 1 }));
        }
      });
      toast(glyphId ? "Character image replaced" : `Added ${label}`, "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not upload that character", "danger");
    } finally {
      lock.current = false;
      setPending(null);
    }
  }

  function uploadControl(label: string, primary: boolean) {
    return (
      <label className={primary ? "btn primary" : "btn secondary"}>
        {busy === "process" ? "Reading the photo…" : label}
        <input
          hidden
          type="file"
          accept="image/*,.png,.jpg,.jpeg,.webp"
          disabled={busy !== null || pending !== null}
          onChange={async (event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (!file) return;
            await readPhoto(file);
          }}
        />
      </label>
    );
  }

  function characterUpload(cardKey: string, ariaLabel: string, onFile: (file: File) => void) {
    const waiting = pending === cardKey;
    return (
      <label className={locked && !waiting ? "btn ghost small is-disabled" : "btn ghost small"}>
        {waiting ? "Reading…" : "Upload"}
        <input
          hidden
          type="file"
          accept="image/*,.png,.jpg,.jpeg,.webp"
          disabled={locked}
          aria-label={ariaLabel}
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (!file) return;
            onFile(file);
          }}
        />
      </label>
    );
  }

  async function removeProfile() {
    const deleted = await confirm({
      title: "Delete profile?",
      message: `"${profile.name}" and its samples will be permanently removed. This cannot be undone.`,
      confirmLabel: "Delete profile",
      action: () => api.deleteProfile(profile.id),
    });
    if (!deleted) return;
    toast("Profile deleted", "success");
    router.push("/handwriting");
  }

  return (
    <>
      {dialog}
      <div className="row" style={{ marginBottom: 16, justifyContent: "space-between" }}>
        <div>
          <button className="btn ghost" onClick={() => router.push("/handwriting")}>Handwriting</button>
          <h1 style={{ fontSize: 22, marginTop: 8 }}>HandFonted</h1>
          <p className="secondary">Upload as many photos as you need. Each photo should contain A–Z, a–z, and 0–9. If one is missing, or the reader got it wrong, upload a picture of that single character. A batch uses a different drawing each time a character appears.</p>
        </div>
        <div className="row">
          <Badge value={profile.status} />
          <button className="btn danger" type="button" onClick={() => { void removeProfile(); }}>Delete</button>
        </div>
      </div>

      <section className="upload-examples" aria-labelledby="upload-examples-title">
        <h2 id="upload-examples-title">Image Upload Examples:</h2>
        <div className="upload-examples-grid">
          <figure className="upload-example">
            <img src="/assets/Sample1.jpeg" alt="Plain paper with each letter written clearly and kept apart" />
            <figcaption className="is-good">Good: Clear, separated</figcaption>
          </figure>
          <figure className="upload-example">
            <img src="/assets/bad_example.jpg" alt="Lined notebook paper with letters joined together" />
            <figcaption className="is-bad">Bad: Lined background, connected</figcaption>
          </figure>
        </div>
      </section>

      <section className="card">
        <h2>1. Photos</h2>
        <p className="sub">Use a dark pen and keep the characters apart. {sets.length} {sets.length === 1 ? "sample" : "samples"} uploaded.</p>
        <div className="grid-2">
          <div className="field">
            <label>Profile name</label>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              onBlur={async () => {
                const trimmed = name.trim();
                if (!trimmed || trimmed === profile.name) return;
                try {
                  onProfile(await api.updateProfile(profile.id, { name: trimmed }));
                } catch (err) {
                  toast(err instanceof Error ? err.message : "Could not rename", "danger");
                }
              }}
            />
          </div>
          <div className="field">
            <label>Stroke thickness ({thickness})</label>
            <input
              type="range"
              min={40}
              max={180}
              step={10}
              value={thickness}
              onChange={(event) => setThickness(Number(event.target.value))}
              onMouseUp={async (event) => {
                const value = Number(event.currentTarget.value);
                if (!glyphs.length || lock.current) return;
                enqueue(() => saveGlyphs(glyphs, value)).catch((err: Error) => toast(err.message, "danger"));
              }}
            />
          </div>
        </div>
        {sets.length === 0 ? (
          <div className="row" style={{ marginTop: 12 }}>
            {uploadControl("Upload and read photo", true)}
            <span className="secondary">No photo yet</span>
          </div>
        ) : (
          <p className="secondary" style={{ marginTop: 12 }}>{kept.length} characters kept across {sets.length} {sets.length === 1 ? "sample" : "samples"}.</p>
        )}
      </section>

      <section className="card" style={{ marginTop: 14 }}>
        <h2>2. Characters</h2>
        <p className="sub">Each sample stays in its own set. Correct a wrong label, remove a mark that is not a character, or upload one character when it is missing or the picture is wrong. Copies of the same character are kept and used in turn.</p>
        {sets.length === 0 ? (
          <p className="secondary">Upload a photo to see the characters.</p>
        ) : sets.map(([number, rows]) => {
          const present = labelsInSample(rows);
          const missing = [...ALPHABET].filter((char) => !present.has(char));
          return (
          <div className="sample-block" key={number}>
            <h3>Sample {number} <span className="muted">{present.size} of 62</span></h3>
            <div className="glyph-grid">
              {rows.map((glyph) => (
                <article key={glyph.id} className={glyph.kept ? "glyph-card" : "glyph-card off"}>
                  <img
                    className="glyph-ink"
                    alt={glyph.label || "Unlabeled character"}
                    src={`${API_URL}/api/profiles/${profile.id}/handfonted/glyphs/${glyph.id}?v=${revisions[glyph.id] ?? 0}`}
                  />
                  <input
                    maxLength={1}
                    value={glyph.label}
                    aria-label={`Sample ${number} character`}
                    disabled={!glyph.kept || locked}
                    onChange={(event) => replace(glyph.id, { label: event.target.value })}
                    onBlur={(event) => {
                      if (lock.current) return;
                      const next = glyphs.map((item) => (
                        item.id === glyph.id ? { ...item, label: event.target.value.slice(0, 1) } : item
                      ));
                      setGlyphs(next);
                      enqueue(() => saveGlyphs(next)).catch((err: Error) => toast(err.message, "danger"));
                    }}
                  />
                  <button
                    className="btn ghost small"
                    type="button"
                    disabled={locked}
                    onClick={() => {
                      if (lock.current) return;
                      const next = replace(glyph.id, { kept: !glyph.kept });
                      enqueue(() => saveGlyphs(next)).catch((err: Error) => toast(err.message, "danger"));
                    }}
                  >{glyph.kept ? "Remove" : "Restore"}</button>
                  {characterUpload(
                    glyph.id,
                    `Upload a replacement for ${glyph.label || "this character"}`,
                    (file) => { void uploadCharacter(file, { glyphId: glyph.id }); },
                  )}
                  <span className="muted">{glyph.manual ? "Uploaded" : `${Math.round(glyph.confidence * 100)}%`}</span>
                </article>
              ))}
              {missing.map((char) => (
                <article key={`${number}-${char}`} className="glyph-card missing">
                  <div className="glyph-missing" aria-hidden="true">{char}</div>
                  <span className="muted">Missing</span>
                  {characterUpload(
                    `${number}:${char}`,
                    `Upload ${char} for sample ${number}`,
                    (file) => { void uploadCharacter(file, { label: char, sample: number }); },
                  )}
                </article>
              ))}
            </div>
          </div>
          );
        })}
        {sets.length > 0 ? (
          <div className="row" style={{ marginTop: 16 }}>
            {uploadControl("Upload another sample", false)}
          </div>
        ) : null}
        <div className="row" style={{ marginTop: 14, justifyContent: "flex-end" }}>
          <button
            className="btn primary"
            disabled={locked || kept.length === 0}
            onClick={async () => {
              if (lock.current) return;
              lock.current = true;
              setBusy("font");
              try {
                await enqueue(async () => {
                  const trimmed = name.trim();
                  if (trimmed && trimmed !== profile.name) {
                    await api.updateProfile(profile.id, { name: trimmed });
                  }
                  const saved = await api.generateHandfonted(profile.id, glyphs, thickness);
                  onProfile(saved);
                });
                toast("Handwriting saved", "success");
                try {
                  await showPreview(sample);
                } catch (err) {
                  toast(err instanceof Error ? err.message : "The handwriting is saved, but the preview did not draw.", "danger");
                }
              } catch (err) {
                toast(err instanceof Error ? err.message : "Could not save the handwriting", "danger");
              } finally {
                lock.current = false;
                setBusy(null);
              }
            }}
          >{busy === "font" ? "Saving…" : "Save handwriting"}</button>
        </div>
      </section>

      <section className="card" style={{ marginTop: 14 }}>
        <h2>3. Preview</h2>
        <p className="sub">Type a sentence. Letters sit on one baseline. A repeated letter stays the same inside a word, and the next word can use another drawing. Commas, periods, colons, quotes, and apostrophes are drawn from the handwriting font.</p>
        {kept.length ? (
          <>
            <div className="field">
              <label>Sample text</label>
              <input
                value={sample}
                onChange={(event) => setSample(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key !== "Enter" || lock.current) return;
                  event.preventDefault();
                  lock.current = true;
                  setBusy("preview");
                  showPreview(sample).catch((err: Error) => toast(err.message, "danger")).finally(() => {
                    lock.current = false;
                    setBusy(null);
                  });
                }}
              />
            </div>
            <div className="row" style={{ marginTop: 12 }}>
              <button
                className="btn secondary"
                disabled={locked || !sample.trim()}
                onClick={async () => {
                  if (lock.current) return;
                  lock.current = true;
                  setBusy("preview");
                  try {
                    await showPreview(sample);
                  } catch (err) {
                    toast(err instanceof Error ? err.message : "Could not preview", "danger");
                  } finally {
                    lock.current = false;
                    setBusy(null);
                  }
                }}
              >{busy === "preview" ? "Drawing…" : "Preview text"}</button>
            </div>
            {preview ? <img className="font-preview" alt="Font preview" src={preview} /> : <p className="secondary" style={{ marginTop: 12 }}>Save the handwriting, then preview a sentence.</p>}
          </>
        ) : <p className="secondary">The preview appears after a sample is read.</p>}
      </section>
    </>
  );
}
