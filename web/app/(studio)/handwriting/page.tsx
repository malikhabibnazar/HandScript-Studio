"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BackLink, Badge, Empty, Modal, PageHeader, useToast } from "@/components/ui";
import { Icon } from "@/components/icons";
import { api } from "@/lib/api";
import type { HandwritingEngineName, HandwritingStatus, Profile } from "@/lib/types";

type ProfileSource = "image" | "draw";
import { ENGINE_LABEL, RendererPicker } from "@/components/renderer-choice";

export default function HandwritingPage() {
  const router = useRouter();
  const toast = useToast();
  const [rows, setRows] = useState<Profile[] | null>(null);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [source, setSource] = useState<ProfileSource>("image");
  const [engine, setEngine] = useState<HandwritingEngineName>("pillow");
  const [face, setFace] = useState<"caveat" | "homemade" | "patrick" | "kalam" | "sacramento" | "architects">("caveat");
  const [status, setStatus] = useState<HandwritingStatus | null>(null);

  function load() {
    api.profiles().then(setRows).catch((err: Error) => toast(err.message, "danger"));
  }
  useEffect(() => {
    load();
    api.handwritingStatus().then(setStatus).catch(() => setStatus(null));
  }, []);
  if (!rows) return <><div className="page-back"><BackLink href="/dashboard" /></div><div className="loading">Loading profiles…</div></>;

  return (
    <>
      <div className="page-back"><BackLink href="/dashboard" /></div>
      <PageHeader title="Handwriting" subtitle="Image profiles use an uploaded sample. Draw profiles place each letter on its own.">
        <button className="btn primary" onClick={() => setOpen(true)}><Icon name="plus" size={16} /> New Profile</button>
      </PageHeader>
      {rows.length === 0 ? <Empty title="No profiles" body="Create an image profile, or draw each letter in a print style." /> : (
        <div className="cards">
          {rows.map((item) => (
            <button key={item.id} className="card preview-card" onClick={() => router.push(`/handwriting/${item.id}`)}>
              <p className="hand">{item.preview_text}</p>
              <div className="row" style={{ justifyContent: "space-between", marginTop: 12 }}>
                <strong>{item.name}</strong>
                <Badge value={item.status} />
              </div>
              {item.is_default ? <p className="muted">Default profile</p> : null}
              <p className="muted" style={{ marginTop: 6 }}>{item.style?.engine === "drawn" ? "Drawn letters" : `${item.sample_count} samples · ${ENGINE_LABEL[item.style?.engine ?? "graves"]}`}</p>
              <p className="secondary" style={{ marginTop: 8 }}>{item.description}</p>
            </button>
          ))}
        </div>
      )}
      {open ? (
        <Modal title="New handwriting profile" onClose={() => setOpen(false)}>
          <div className="stack" style={{ marginTop: 14 }}>
            <div className="field"><label>Name</label><input value={name} onChange={(event) => setName(event.target.value)} /></div>
            <div className="field"><label>Description</label><textarea value={description} onChange={(event) => setDescription(event.target.value)} /></div>
            <div className="field">
              <label>How should this profile be made?</label>
              <div className="stack">
                <button type="button" className={source === "image" ? "option on" : "option"} onClick={() => setSource("image")}>
                  <span className="radio" />
                  <span><strong>Image based</strong><br /><span className="secondary">Upload a photo or specimen sheet and pick one of the current renderers.</span></span>
                </button>
                <button type="button" className={source === "draw" ? "option on" : "option"} onClick={() => setSource("draw")}>
                  <span className="radio" />
                  <span><strong>Draw based</strong><br /><span className="secondary">Draw each letter. The page is built by placing those letters separately, in a print style.</span></span>
                </button>
              </div>
            </div>
            {source === "image" ? (
              <div className="field">
                <label>Renderer</label>
                <RendererPicker engine={engine} face={face} status={status} onEngine={setEngine} onFace={setFace} />
              </div>
            ) : null}
            <div className="row" style={{ justifyContent: "flex-end" }}>
              <button className="btn primary" disabled={!name.trim()} onClick={async () => {
                const created = await api.createProfile(source === "draw"
                  ? { name, description, engine: "drawn" }
                  : { name, description, engine, font_family: face });
                router.push(`/handwriting/${created.id}`);
              }}>Create</button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
