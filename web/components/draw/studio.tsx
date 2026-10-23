"use client";

import { useEffect, useState } from "react";
import { api, glyphImageUrl } from "@/lib/api";
import type { GlyphInventory, GlyphSetName, Profile, ProfileStyle } from "@/lib/types";
import { useConfirm, useToast } from "@/components/ui";
import { CharacterGrid } from "./character-grid";
import { DrawPad, type InkExport } from "./pad";
import { LivePreview } from "./live-preview";
import { StyleControls } from "./style-controls";

function countFor(inventory: GlyphInventory, setName: GlyphSetName) {
  return setName === "set1" ? inventory.set1_count : inventory.set2_count;
}

export function DrawStudio({
  profile,
  style,
  onProfile,
  onStyle,
}: {
  profile: Profile;
  style: ProfileStyle;
  onProfile: (profile: Profile) => void;
  onStyle: (style: ProfileStyle) => void;
}) {
  const toast = useToast();
  const { confirm, dialog } = useConfirm();
  const [inventory, setInventory] = useState<GlyphInventory | null>(null);
  const [setName, setSetName] = useState<GlyphSetName>("set1");
  const [selectedKey, setSelectedKey] = useState("");
  const [text, setText] = useState(profile.preview_text);
  const [stamp, setStamp] = useState(0);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    api.glyphs(profile.id).then((next) => {
      setInventory(next);
      setSelectedKey((current) => current || next.slots[0]?.key || "");
    }).catch((err: Error) => toast(err.message, "danger"));
  }, [profile.id]);

  useEffect(() => {
    const timer = setTimeout(() => {
      api.updateProfile(profile.id, { style: { ...style, engine: "drawn", source: "draw" } }).then((saved) => {
        onProfile(saved);
        if (saved.style) onStyle(saved.style);
        setRevision((value) => value + 1);
      }).catch((err: Error) => toast(err.message, "danger"));
    }, 350);
    return () => clearTimeout(timer);
  }, [profile.id, style.word_size_px, style.word_spacing_px, style.char_spacing_px, style.variation, style.ink_color]);

  useEffect(() => {
    const timer = setTimeout(() => {
      api.updateProfile(profile.id, { preview_text: text }).catch((err: Error) => toast(err.message, "danger"));
    }, 400);
    return () => clearTimeout(timer);
  }, [profile.id, text]);

  const selected = inventory?.slots.find((slot) => slot.key === selectedKey) ?? null;
  const saved = selected ? (setName === "set1" ? selected.set1 : selected.set2) : null;
  const activeCount = inventory ? countFor(inventory, setName) : 0;
  const total = inventory?.total ?? 90;

  async function refresh(next: GlyphInventory, message: string) {
    setInventory(next);
    setStamp((value) => value + 1);
    setRevision((value) => value + 1);
    onProfile(await api.profile(profile.id));
    toast(message, "success");
  }

  async function saveLetter(ink: InkExport) {
    if (!selected) return;
    const next = await api.saveGlyph(profile.id, setName, selected.key, ink.blob, {
      baselineY: ink.baselineY,
      padWidth: ink.padWidth,
      padHeight: ink.padHeight,
      cropLeft: ink.cropLeft,
      cropTop: ink.cropTop,
    });
    await refresh(next, `Saved ${selected.char}`);
  }

  async function clearSet() {
    let next: GlyphInventory | null = null;
    const cleared = await confirm({
      title: "Clear sample set?",
      message: "Every drawn letter in both sets will be permanently removed. This cannot be undone.",
      confirmLabel: "Clear sample set",
      action: async () => {
        next = await api.clearGlyphs(profile.id);
      },
    });
    if (!cleared || !next) return;
    await refresh(next, "Sample set cleared").catch((err: Error) => toast(err.message, "danger"));
  }

  async function removeLetter() {
    if (!selected) return;
    const setLabel = setName === "set1" ? "Set 1" : "Set 2";
    const letter = selected;
    let next: GlyphInventory | null = null;
    const removed = await confirm({
      title: "Delete this letter?",
      message: `The drawing for "${letter.char}" in ${setLabel} will be permanently removed.`,
      confirmLabel: "Delete letter",
      action: async () => {
        next = await api.deleteGlyph(profile.id, setName, letter.key);
      },
    });
    if (!removed || !next) return;
    await refresh(next, `Removed ${letter.char}`).catch((err: Error) => toast(err.message, "danger"));
  }

  return (
    <>
      {dialog}
      <div className="draw-studio">
      <div className="stack">
        <section className="card">
          <div className="row" style={{ justifyContent: "space-between", gap: 12 }}>
            <div>
              <h2>Shape your script</h2>
              <p className="sub">Draw each character by itself. Set 2 is a second copy of the same letter, used so repeats are not identical.</p>
            </div>
            <div className="row">
              <button type="button" className="btn secondary" onClick={() => {
                api.restoreGlyphs(profile.id).then((next) => refresh(next, "Sample set restored")).catch((err: Error) => toast(err.message, "danger"));
              }}>Restore sample set</button>
              <button type="button" className="btn secondary" onClick={() => { void clearSet(); }}>Clear sample set</button>
            </div>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <button type="button" className={setName === "set1" ? "btn primary" : "btn secondary"} onClick={() => setSetName("set1")}>Set 1</button>
            <button type="button" className={setName === "set2" ? "btn primary" : "btn secondary"} onClick={() => setSetName("set2")}>Set 2</button>
            <span className="secondary">{setName === "set1" ? "Set 1" : "Set 2"}: {activeCount}/{total}</span>
          </div>
          <div className="meter" style={{ marginTop: 8 }}><span style={{ width: `${total ? (activeCount / total) * 100 : 0}%` }} /></div>
          {inventory ? (
            <CharacterGrid
              profileId={profile.id}
              inventory={inventory}
              setName={setName}
              selectedKey={selectedKey}
              stamp={stamp}
              onSelect={setSelectedKey}
            />
          ) : <p className="secondary">Loading letters…</p>}
          {selected && inventory ? (
            <div className="draw-workspace">
              <div>
                <h3>Draw {selected.char}</h3>
                <DrawPad
                  padWidth={inventory.pad_width}
                  padHeight={inventory.pad_height}
                  baselineY={inventory.baseline_y}
                  resetKey={`${setName}-${selected.key}`}
                  onSave={saveLetter}
                />
              </div>
              <div>
                <h3>Saved</h3>
                {saved ? (
                  <>
                    <img className="saved-glyph" src={glyphImageUrl(profile.id, setName, selected.key, stamp)} alt={`Saved ${selected.char}`} />
                    <button type="button" className="btn secondary" onClick={() => { void removeLetter(); }}>Delete this letter</button>
                  </>
                ) : <p className="secondary">Not drawn in this set yet.</p>}
              </div>
            </div>
          ) : null}
        </section>
        <section className="card">
          <h2>Style</h2>
          <p className="sub">Size and spacing apply when a document is generated. Letters stay separate.</p>
          <StyleControls style={style} onChange={onStyle} />
        </section>
      </div>
      <LivePreview profileId={profile.id} text={text} revision={revision} onText={setText} />
    </div>
    </>
  );
}
