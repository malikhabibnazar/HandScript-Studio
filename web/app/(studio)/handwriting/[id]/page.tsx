"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { BackLink, Badge, useConfirm, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { RendererPicker } from "@/components/renderer-choice";
import { DrawStudio } from "@/components/draw/studio";
import { HandfontedStudio } from "@/components/handfonted-studio";
import type { DrawfontCapture, HandwritingStatus, PillowFace, Profile, ProfileStyle } from "@/lib/types";

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
  capture: "minimal",
  chars: "",
  smooth: 1,
  weight: 0,
  thickness: 100,
  glyphs: [],
};

const DRAWFONT_CAPTURES: { id: DrawfontCapture; title: string; body: string }[] = [
  { id: "minimal", title: "Template · minimal", body: "Print the sheet. Write A–Z, a–z, digits, and common punctuation in the printed cells." },
  { id: "spanish", title: "Template · Spanish", body: "The minimal sheet plus ñ and accented letters." },
  { id: "freeform", title: "Freeform photo", body: "Any paper. Letters must not touch. Type them below in the order you wrote them." },
];

export default function HandwritingDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [text, setText] = useState("");
  const [style, setStyle] = useState<ProfileStyle>(DEFAULT_STYLE);
  const [engine, setEngine] = useState<HandwritingStatus | null>(null);
  const { confirm, dialog } = useConfirm();

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

  async function removeProfile() {
    if (!profile) return;
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

  if (!profile) return <><div className="page-back"><BackLink href="/handwriting" /></div><div className="loading">Loading profile…</div></>;
  if (profile.style?.engine === "handfonted") {
    return <HandfontedStudio profile={profile} onProfile={setProfile} />;
  }
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
      {dialog}
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
          <button className="btn danger" type="button" onClick={() => { void removeProfile(); }}>Delete</button>
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
              {style.engine === "drawfont" ? (
                <>
                  <p className="sub">How this photo is labeled. A template uses the printed order. A freeform photo uses the letters you type, in writing order.</p>
                  {DRAWFONT_CAPTURES.map((choice) => (
                    <button
                      key={choice.id}
                      type="button"
                      className={style.capture === choice.id ? "option on" : "option"}
                      onClick={() => saveStyle({ ...style, capture: choice.id })}
                    >
                      <span className="radio" />
                      <span><strong>{choice.title}</strong><br /><span className="secondary">{choice.body}</span></span>
                    </button>
                  ))}
                  {style.capture === "freeform" ? (
                    <div className="field">
                      <label>Letters in writing order</label>
                      <input
                        value={style.chars}
                        placeholder="ABCabc0123.,!"
                        onChange={(event) => setStyle({ ...style, chars: event.target.value })}
                        onBlur={(event) => saveStyle({ ...style, chars: event.target.value })}
                      />
                    </div>
                  ) : null}
                  <div className="field">
                    <label>Smoothness ({Number(style.smooth).toFixed(1)})</label>
                    <input
                      type="range"
                      min={0}
                      max={2}
                      step={0.5}
                      value={style.smooth}
                      onChange={(event) => setStyle({ ...style, smooth: Number(event.target.value) })}
                      onMouseUp={(event) => saveStyle({ ...style, smooth: Number(event.currentTarget.value) })}
                      onKeyUp={(event) => saveStyle({ ...style, smooth: Number(event.currentTarget.value) })}
                    />
                  </div>
                  <div className="field">
                    <label>Weight ({Number(style.weight).toFixed(1)})</label>
                    <input
                      type="range"
                      min={-2}
                      max={2}
                      step={0.5}
                      value={style.weight}
                      onChange={(event) => setStyle({ ...style, weight: Number(event.target.value) })}
                      onMouseUp={(event) => saveStyle({ ...style, weight: Number(event.currentTarget.value) })}
                      onKeyUp={(event) => saveStyle({ ...style, weight: Number(event.currentTarget.value) })}
                    />
                  </div>
                  {style.font_error ? <p className="secondary">{style.font_error}</p> : null}
                  {style.font_path ? (
                    <p className="secondary">
                      {style.web_font_path
                        ? "A personal TTF and WOFF2 are saved for this profile."
                        : "A personal font is saved for this profile."}
                    </p>
                  ) : null}
                </>
              ) : null}
              {style.engine !== "drawfont" && style.font_path ? <p className="secondary">A personal font is saved for this profile.</p> : null}
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
                    : style.engine === "drawfont"
                      ? "Upload a freeform photo or a filled draw-your-font template. Use a dark pen and keep the letters apart. The photo stays on this machine and becomes TTF and WOFF2."
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
                event.target.value = "";
                if (!file) return;
                try {
                  if (style.engine === "drawfont") await api.updateProfile(profile.id, { style });
                  const next = await api.uploadSample(profile.id, file);
                  setProfile(next);
                  if (next.style) setStyle({ ...DEFAULT_STYLE, ...next.style });
                  if (next.style?.font_error) toast(next.style.font_error, "danger");
                  else toast("Sample added", "success");
                } catch (err) {
                  toast(err instanceof Error ? err.message : "Could not add the sample", "danger");
                }
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
