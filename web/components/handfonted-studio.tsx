"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge, useConfirm, useToast } from "@/components/ui";
import { API_URL, api } from "@/lib/api";
import type { HandfontedGlyph, Profile } from "@/lib/types";

const MAX_SAMPLES = 4;

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
  const [preview, setPreview] = useState<string | null>(null);
  const [sample, setSample] = useState(profile.preview_text || "The quick brown fox 0123456789");

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
  const atLimit = sets.length >= MAX_SAMPLES;

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
    setBusy("process");
    try {
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
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not read the photo", "danger");
    } finally {
      setBusy(null);
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
          disabled={busy !== null || atLimit}
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
          <p className="secondary">Upload up to four photos. Each photo should contain A–Z, a–z, and 0–9. A batch uses a different drawing each time a character appears.</p>
        </div>
        <div className="row">
          <Badge value={profile.status} />
          <button className="btn danger" type="button" onClick={() => { void removeProfile(); }}>Delete</button>
        </div>
      </div>

      <section className="card">
        <h2>1. Photos</h2>
        <p className="sub">Use a dark pen and keep the characters apart. {sets.length} of {MAX_SAMPLES} samples uploaded.</p>
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
                if (!glyphs.length) return;
                try {
                  await saveGlyphs(glyphs, value);
                } catch (err) {
                  toast(err instanceof Error ? err.message : "Could not save thickness", "danger");
                }
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
        <p className="sub">Each sample stays in its own set. Correct a wrong label, or remove a mark that is not a character. Copies of the same character are kept and used in turn.</p>
        {sets.length === 0 ? (
          <p className="secondary">Upload a photo to see the characters.</p>
        ) : sets.map(([number, rows]) => (
          <div className="sample-block" key={number}>
            <h3>Sample {number}</h3>
            <div className="glyph-grid">
              {rows.map((glyph) => (
                <article key={glyph.id} className={glyph.kept ? "glyph-card" : "glyph-card off"}>
                  <img
                    className="glyph-ink"
                    alt={glyph.label || "Unlabeled character"}
                    src={`${API_URL}/api/profiles/${profile.id}/handfonted/glyphs/${glyph.id}`}
                  />
                  <input
                    maxLength={1}
                    value={glyph.label}
                    aria-label={`Sample ${number} character`}
                    disabled={!glyph.kept}
                    onChange={(event) => replace(glyph.id, { label: event.target.value })}
                    onBlur={(event) => {
                      const next = glyphs.map((item) => (
                        item.id === glyph.id ? { ...item, label: event.target.value.slice(0, 1) } : item
                      ));
                      setGlyphs(next);
                      saveGlyphs(next).catch((err: Error) => toast(err.message, "danger"));
                    }}
                  />
                  <button
                    className="btn ghost small"
                    type="button"
                    onClick={() => {
                      const next = replace(glyph.id, { kept: !glyph.kept });
                      saveGlyphs(next).catch((err: Error) => toast(err.message, "danger"));
                    }}
                  >{glyph.kept ? "Remove" : "Restore"}</button>
                  <span className="muted">{Math.round(glyph.confidence * 100)}%</span>
                </article>
              ))}
            </div>
          </div>
        ))}
        {sets.length > 0 ? (
          <div className="row" style={{ marginTop: 16 }}>
            {atLimit ? (
              <span className="secondary">Four samples is the maximum for this profile.</span>
            ) : uploadControl("Upload another sample", false)}
          </div>
        ) : null}
        <div className="row" style={{ marginTop: 14, justifyContent: "flex-end" }}>
          <button
            className="btn primary"
            disabled={busy !== null || kept.length === 0}
            onClick={async () => {
              setBusy("font");
              try {
                const trimmed = name.trim();
                if (trimmed && trimmed !== profile.name) {
                  await api.updateProfile(profile.id, { name: trimmed });
                }
                const saved = await api.generateHandfonted(profile.id, glyphs, thickness);
                onProfile(saved);
                toast("Handwriting saved", "success");
                try {
                  await showPreview(sample);
                } catch (err) {
                  toast(err instanceof Error ? err.message : "The handwriting is saved, but the preview did not draw.", "danger");
                }
              } catch (err) {
                toast(err instanceof Error ? err.message : "Could not save the handwriting", "danger");
              } finally {
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
                  if (event.key === "Enter") {
                    event.preventDefault();
                    setBusy("preview");
                    showPreview(sample).catch((err: Error) => toast(err.message, "danger")).finally(() => setBusy(null));
                  }
                }}
              />
            </div>
            <div className="row" style={{ marginTop: 12 }}>
              <button
                className="btn secondary"
                disabled={busy !== null || !sample.trim()}
                onClick={async () => {
                  setBusy("preview");
                  try {
                    await showPreview(sample);
                  } catch (err) {
                    toast(err instanceof Error ? err.message : "Could not preview", "danger");
                  } finally {
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
