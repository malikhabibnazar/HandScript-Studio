"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { BackLink, Badge, useToast } from "@/components/ui";
import { api, previewUrl } from "@/lib/api";
import type { DocumentDetail, Element, Profile } from "@/lib/types";

const DocumentCanvas = dynamic(() => import("@/components/canvas").then((mod) => mod.DocumentCanvas), { ssr: false });

export default function DocumentEditorPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [elements, setElements] = useState<Element[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [grid, setGrid] = useState(true);

  useEffect(() => {
    api.document(params.id).then((next) => {
      setDoc(next);
      const fields = next.fields || {};
      setElements((next.template?.elements || []).map((el) => ({ ...el, content: fields[el.id] ?? el.content })));
    }).catch((err: Error) => toast(err.message, "danger"));
    api.profiles().then(setProfiles).catch(() => undefined);
  }, [params.id, toast]);

  if (!doc || !doc.template) return <><div className="page-back"><BackLink href="/documents" /></div><div className="loading">Loading document…</div></>;
  const currentDoc = doc;
  const template = doc.template;
  const current = elements.find((el) => el.id === selected) || null;

  function updateElement(id: string, patch: Partial<Element>) {
    setElements((items) => items.map((el) => el.id === id ? { ...el, ...patch } : el));
  }

  async function save() {
    const fields: Record<string, string> = {};
    elements.forEach((el) => { fields[el.id] = el.content; });
    const saved = await api.updateDocument(currentDoc.id, {
      name: currentDoc.name,
      profile_id: currentDoc.profile_id,
      status: currentDoc.status,
      export_format: currentDoc.export_format,
      fields,
    });
    setDoc(saved);
    toast("Document saved", "success");
  }

  return (
    <>
      <div className="row" style={{ marginBottom: 12, justifyContent: "space-between" }}>
        <div className="row">
          <BackLink href="/documents" />
          <strong>{currentDoc.name}</strong>
          <Badge value={currentDoc.status} />
        </div>
        <div className="row">
          <button className="btn secondary small" onClick={() => setGrid((value) => !value)}>{grid ? "Hide grid" : "Show grid"}</button>
          <button className="btn secondary small" onClick={() => setZoom((value) => Math.max(0.6, value - 0.1))}>−</button>
          <span className="muted">{Math.round(zoom * 100)}%</span>
          <button className="btn secondary small" onClick={() => setZoom((value) => Math.min(1.8, value + 0.1))}>+</button>
          <a className="btn secondary" href={previewUrl(currentDoc.id)} target="_blank" rel="noreferrer">Preview file</a>
          <button className="btn primary" onClick={save}>Save</button>
        </div>
      </div>
      <div className="editor">
        <aside className="panel stack">
          <div className="field"><label>Name</label><input value={currentDoc.name} onChange={(event) => setDoc({ ...currentDoc, name: event.target.value })} /></div>
          <div className="field"><label>Template</label><input value={template.name} readOnly /></div>
          <div className="field"><label>Profile</label>
            <select value={currentDoc.profile_id} onChange={(event) => {
              const profile = profiles.find((item) => item.id === event.target.value);
              setDoc({ ...currentDoc, profile_id: event.target.value, profile_name: profile?.name || currentDoc.profile_name });
            }}>
              {profiles.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </div>
          <div className="field"><label>Status</label>
            <select value={currentDoc.status} onChange={(event) => setDoc({ ...currentDoc, status: event.target.value })}>
              {["Draft", "Ready", "Generating", "Completed", "Failed"].map((item) => <option key={item}>{item}</option>)}
            </select>
          </div>
          <div className="field"><label>Export format</label>
            <select value={currentDoc.export_format} onChange={(event) => setDoc({ ...currentDoc, export_format: event.target.value })}>
              {["PDF", "PNG", "Combined PDF"].map((item) => <option key={item}>{item}</option>)}
            </select>
          </div>
          <p className="muted">Page {template.width_in} × {template.height_in} in · safe area {template.margin_in} in</p>
        </aside>
        <DocumentCanvas
          widthIn={template.width_in}
          heightIn={template.height_in}
          marginIn={template.margin_in}
          elements={elements}
          selectedId={selected}
          zoom={zoom}
          showGrid={grid}
          editable={false}
          onSelect={setSelected}
        />
        <aside className="panel stack">
          <h2>Inspector</h2>
          {current ? (
            <>
              <strong>{current.name}</strong>
              <span className="muted">{current.type}</span>
              <div className="field"><label>Content</label>
                <textarea value={current.content} onChange={(event) => updateElement(current.id, { content: event.target.value })} />
              </div>
              <p className="muted">Use {"{first_name}"} style placeholders. They are filled during a batch.</p>
            </>
          ) : <p className="secondary">Select a block on the page to edit its text.</p>}
        </aside>
      </div>
    </>
  );
}
