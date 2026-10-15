"use client";

import { API_URL } from "@/lib/api";
import type { HandwritingEngineName, HandwritingStatus, PillowFace } from "@/lib/types";

export const ENGINE_LABEL: Record<HandwritingEngineName, string> = {
  gemini: "HandwritingAgent",
  onedm: "One-DM (Diffusion)",
  pillow: "Handwriting font",
  handwrite: "Handwrite",
  hw2font: "hw2font",
  fontmaker: "Font maker",
  graves: "Graves AI",
};

const CHOICES: { id: HandwritingEngineName; title: string; body: string }[] = [
  { id: "onedm", title: "One-DM (Diffusion)", body: "One-shot diffusion mimicker (ECCV 2024). Clones your uploaded handwriting sample using AMD Radeon RX 580 (DirectML), CUDA, or CPU." },
  { id: "gemini", title: "HandwritingAgent", body: "Gemini reads the handwriting photo on this profile and draws only the card text in that hand." },
  { id: "pillow", title: "Handwriting font", body: "Adult handwriting drawn locally with Pillow. Pick a face below. No extra tools." },
  { id: "handwrite", title: "Handwrite", body: "The handwrite library. A filled sample sheet becomes a personal font when FontForge and Potrace are installed." },
  { id: "hw2font", title: "hw2font", body: "Print the hw2font sheet, scan it, and upload it. Potrace and FontForge build an OpenType font with spacing and alternates." },
  { id: "fontmaker", title: "Font maker", body: "Print the marker sheet and photograph the whole page. Corner markers line the scan up before the font is built." },
  { id: "graves", title: "Graves AI", body: "Stroke model. Style, bias and variation change the hand." },
];

export function RendererPicker({
  engine,
  face,
  status,
  onEngine,
  onFace,
}: {
  engine: HandwritingEngineName;
  face: PillowFace;
  status: HandwritingStatus | null;
  onEngine: (engine: HandwritingEngineName) => void;
  onFace: (face: PillowFace) => void;
}) {
  const sheetsReady = Boolean(status?.sheets?.personal_font);
  const sheetNote = sheetsReady
    ? "FontForge and Potrace are available. Upload a filled sheet and this profile will print with that font."
    : "Pages use a built-in handwriting face until FontForge and Potrace are installed and a filled sheet is uploaded.";

  return (
    <div className="stack">
      {CHOICES.map((choice) => (
        <button key={choice.id} type="button" className={engine === choice.id ? "option on" : "option"} onClick={() => onEngine(choice.id)}>
          <span className="radio" />
          <span><strong>{choice.title}</strong><br /><span className="secondary">{choice.body}</span></span>
        </button>
      ))}
      {engine === "pillow" ? (
        <div className="field">
          <label>Face</label>
          <div className="stack">
            {(status?.faces?.length ? status.faces : [
              { id: "caveat" as const, label: "Caveat" },
              { id: "homemade" as const, label: "Homemade Apple" },
              { id: "patrick" as const, label: "Patrick Hand" },
              { id: "kalam" as const, label: "Kalam" },
              { id: "sacramento" as const, label: "Sacramento" },
              { id: "architects" as const, label: "Architects Daughter" },
            ]).map((item) => (
              <button key={item.id} type="button" className={face === item.id ? "option on" : "option"} onClick={() => onFace(item.id)}>
                <span className="radio" />
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}
      {engine === "hw2font" || engine === "fontmaker" ? (
        <p className="secondary">
          {sheetNote}{" "}
          <a href={`${API_URL}/api/handwriting/templates/${engine}.pdf`} download>Download the sheet</a>.
        </p>
      ) : null}
      {engine === "gemini" ? (
        <p className="secondary">
          {status?.gemini && !status.gemini.configured
            ? "GEMINI_API_KEY is not set on the API. Add it and restart the API, then upload a handwriting photo."
            : "Upload a clear photo of the handwriting to copy. Gemini writes only the text already on the card. A reply that adds or changes words is rejected. The API uses the strongest Gemini model this key can call. Each text block is one call."}
        </p>
      ) : null}
      {engine === "onedm" ? (
        <p className="secondary">
          {status?.onedm?.device_label ? `Active Hardware: ${status.onedm.device_label}. ` : ""}
          {status?.onedm?.weights_loaded
            ? "One-DM diffusion checkpoint is loaded. Upload a single clear photo or line of your handwriting, and the diffusion model mimics that style for every card!"
            : "One-DM is ready! Upload a handwriting photo below. (To enable full neural checkpoints on your AMD RX 580 or CUDA GPU, run the setup script: python -m app.handwriting.onedm.setup_onedm)"}
        </p>
      ) : null}
      {engine === "handwrite" ? (
        <p className="secondary">
          {status?.handwrite?.personal_font
            ? "FontForge and Potrace are available. Upload a filled handwrite sample sheet and this profile will print with that font."
            : "Pages use the built-in Handwrite face. A personal font needs FontForge and Potrace on this machine."}
        </p>
      ) : null}
    </div>
  );
}
