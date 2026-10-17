"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { BackLink, Badge, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { RendererPicker } from "@/components/renderer-choice";
import { DrawStudio } from "@/components/draw/studio";
import type { HandwritingStatus, PillowFace, Profile, ProfileStyle } from "@/lib/types";

const DEFAULT_STYLE: ProfileStyle = {
  style_id: 9,
  bias: 0.75,
  variation: 0.15,
  engine: "graves",
  font_family: "caveat",
  source: "image",
  word_size_px: 70,
  word_spacing_px: 15,
  char_spacing_px: -2.5,
  ink_color: null,
};

export default function HandwritingDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [text, setText] = useState("");
  const [style, setStyle] = useState<ProfileStyle>(DEFAULT_STYLE);
  const [engine, setEngine] = useState<HandwritingStatus | null>(null);

  function load() {
    api.profile(params.id).then((next) => {
      setProfile(next);
      setText(next.preview_text);
      setStyle({ ...DEFAULT_STYLE, ...(next.style ?? {}) });
    }).catch((err: Error) => toast(err.message, "danger"));
  }
  useEffect(() => {
    load();
    api.handwritingStatus().then(setEngine).catch(() => setEngine(null));
  }, [params.id]);

  useEffect(() => {
    if (profile?.status !== "Processing") return;
    const timer = setInterval(load, 1200);
    return () => clearInterval(timer);
  }, [profile?.status]);

  if (!profile) return <><div className="page-back"><BackLink href="/handwriting" /></div><div className="loading">Loading profile…</div></>;
  const current = profile;
  const report = current.analysis;
  const drawn = style.engine === "drawn";

  function saveStyle(next: ProfileStyle) {
    setStyle(next);
    api.updateProfile(current.id, { style: next }).then((saved) => {
      setProfile(saved);
      if (saved.style) setStyle({ ...DEFAULT_STYLE, ...saved.style });
    }).catch((err: Error) => toast(err.message, "danger"));
  }

  return (
    <>
      <div className="row" style={{ marginBottom: 16, justifyContent: "space-between" }}>
        <div>
          <BackLink href="/handwriting" />
          <h1 style={{ fontSize: 22, marginTop: 4 }}>{current.name}</h1>
          <p className="secondary">{current.description}</p>
        </div>
        <div className="row">
          <Badge value={profile.status} />
          {!profile.is_default ? <button className="btn secondary" onClick={async () => { setProfile(await api.defaultProfile(profile.id)); toast("Default profile updated", "success"); }}>Set default</button> : <Badge value="Default" />}
          {drawn ? null : <button className="btn secondary" onClick={async () => {
            try { setProfile(await api.analyzeProfile(profile.id)); toast("Analysis started", "info"); }
            catch (err) { toast(err instanceof Error ? err.message : "Could not analyse", "danger"); }
          }}>Run analysis</button>}
          <button className="btn danger" onClick={async () => {
            try {
              await api.deleteProfile(profile.id);
              router.push("/handwriting");
            } catch (err) { toast(err instanceof Error ? err.message : "Could not delete", "danger"); }
          }}>Delete</button>
        </div>
      </div>
      {drawn ? <DrawStudio profile={current} style={style} onProfile={setProfile} onStyle={setStyle} /> : <>
        <div className="grid-2">
          <section className="card">
            <h2>Preview</h2>
            <p className="sub">A handwriting-style preview of this profile.</p>
            <p className="hand" style={{ minHeight: 72 }}>{text}</p>
            <div className="field"><label>Preview text</label>
              <input value={text} onChange={(event) => setText(event.target.value)} onBlur={() => api.updateProfile(profile.id, { preview_text: text })} />
            </div>
            <div className="stack" style={{ marginTop: 12 }}>
              <div className="field">
                <label>Renderer</label>
                <RendererPicker
                  engine={style.engine}
                  face={style.font_family}
                  status={engine}
                  onEngine={(next) => saveStyle({ ...style, engine: next })}
                  onFace={(next: PillowFace) => saveStyle({ ...style, font_family: next })}
                />
              </div>
              {style.engine === "graves" ? (
                <>
                  <p className="sub">Graves style primer. This selects a built-in hand. It does not clone an uploaded sample.</p>
                  <div className="field"><label>Style id</label>
                    <input type="number" min={0} value={style.style_id} onChange={(event) => setStyle({ ...style, style_id: Number(event.target.value) })} onBlur={(event) => saveStyle({ ...style, style_id: Number(event.target.value) })} />
                  </div>
                  <div className="field"><label>Bias ({style.bias.toFixed(2)})</label>
                    <input type="range" min={0} max={1} step={0.05} value={style.bias} onChange={(event) => setStyle({ ...style, bias: Number(event.target.value) })} onMouseUp={(event) => saveStyle({ ...style, bias: Number(event.currentTarget.value) })} onKeyUp={(event) => saveStyle({ ...style, bias: Number(event.currentTarget.value) })} />
                  </div>
                  <div className="field"><label>Variation ({style.variation.toFixed(2)})</label>
                    <input type="range" min={0} max={0.5} step={0.05} value={style.variation} onChange={(event) => setStyle({ ...style, variation: Number(event.target.value) })} onMouseUp={(event) => saveStyle({ ...style, variation: Number(event.currentTarget.value) })} onKeyUp={(event) => saveStyle({ ...style, variation: Number(event.currentTarget.value) })} />
                  </div>
                  {engine?.style_ids.length ? <p className="secondary">Installed primers: {engine.style_ids.join(", ")}</p> : null}
                  {engine && engine.active !== "graves" ? <p className="secondary">{engine.message}</p> : null}
                </>
              ) : null}
              {style.font_path ? <p className="secondary">A personal font is saved for this profile.</p> : null}
            </div>
          </section>
          <section className="card">
            <h2>Analysis</h2>
            <p className="sub">{profile.status === "Processing" ? "The worker is reading the samples." : "Measurements from the latest run."}</p>
            {report ? (
              <div className="stack">
                {[
                  ["Character coverage", `${report.character_coverage}%`],
                  ["Sample quality", `${report.sample_quality}%`],
                  ["Samples analysed", String(report.samples_analyzed)],
                  ["Stroke width", `${report.avg_stroke_width} mm`],
                  ["Slant", `${report.slant_degrees}°`],
                  ["Baseline", `${report.baseline_stability}%`],
                  ["Spacing", `${report.spacing_consistency}%`],
                ].map(([label, value]) => (
                  <div className="setting-row" key={label}><span>{label}</span><strong>{value}</strong></div>
                ))}
                {report.notes.map((note) => <p key={note} className="secondary">{note}</p>)}
              </div>
            ) : <p className="secondary">{profile.status === "Error" ? "The last run did not finish. Add a sample or run analysis again." : "No report yet."}</p>}
          </section>
        </div>
        <section className="card" style={{ marginTop: 14 }}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <div>
              <h2>Samples</h2>
              <p className="sub">{
                style.engine === "onedm"
                  ? "One-DM only needs one clear photo or line of your handwriting. The diffusion model extracts its style features and imitates it for every card."
                  : style.engine === "gemini"
                    ? "Upload a clear photo or scan of the handwriting to copy. HandwritingAgent uses that photo and does not fall back to a font."
                    : style.engine === "hw2font" || style.engine === "fontmaker" || style.engine === "handwrite"
                      ? "Upload a filled specimen sheet. FontForge and Potrace turn it into this profile’s font."
                      : style.engine === "pillow"
                        ? "Stored with the profile. This renderer uses the selected handwriting font."
                        : "Stored with the profile. Graves uses a style primer, not these photos."
              }</p>
            </div>
            <label className="btn secondary">
              Upload sample
              <input hidden type="file" accept="image/*,.png,.jpg,.jpeg,.webp" onChange={async (event) => {
                const file = event.target.files?.[0];
                if (!file) return;
                setProfile(await api.uploadSample(profile.id, file));
                toast("Sample added", "success");
              }} />
            </label>
          </div>
          <div className="table-wrap" style={{ marginTop: 12 }}>
            <table>
              <thead><tr><th>File</th><th>Added</th><th>Quality</th><th>Glyphs</th></tr></thead>
              <tbody>
                {profile.samples.map((sample) => (
                  <tr key={sample.id}>
                    <td>{sample.filename}</td>
                    <td>{formatDate(sample.added)}</td>
                    <td>{sample.quality}</td>
                    <td>{sample.characters}</td>
                  </tr>
                ))}
                {profile.samples.length === 0 ? <tr><td colSpan={4}>No samples yet.</td></tr> : null}
              </tbody>
            </table>
          </div>
        </section>
      </>}
    </>
  );
}
