"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { BackLink, Badge, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import type { Element, Template } from "@/lib/types";

const DocumentCanvas = dynamic(() => import("@/components/canvas").then((mod) => mod.DocumentCanvas), { ssr: false });

function newElement(type: string): Element {
  const id = `el-${Math.random().toString(16).slice(2, 8)}`;
  if (type === "Divider") {
    return { id, type, name: "Divider", x: 0.4, y: 2, width: 5, height: 0.04, align: "left", font_size: 12, content: "", visible: true };
  }
  return {
    id, type, name: type, x: 0.5, y: 0.5, width: 3.2, height: 0.7, align: "left", font_size: 16,
    content: type === "Address" ? "{first_name} {last_name}\n{street}\n{city}, {state} {zip}" : "New text",
    visible: true,
  };
}

export default function TemplateEditorPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const [template, setTemplate] = useState<Template | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [zoom, setZoom] = useState(0.9);

  useEffect(() => {
    api.template(params.id).then(setTemplate).catch((err: Error) => toast(err.message, "danger"));
  }, [params.id, toast]);

  if (!template) return <><div className="page-back"><BackLink href="/templates" /></div><div className="loading">Loading template…</div></>;
  const currentTemplate = template;
  const current = template.elements.find((el) => el.id === selected) || null;

  function patchElement(id: string, patch: Partial<Element>) {
    setTemplate((item) => item ? { ...item, elements: item.elements.map((el) => el.id === id ? { ...el, ...patch } : el) } : item);
  }

  async function save() {
    const saved = await api.updateTemplate(currentTemplate.id, {
      name: currentTemplate.name,
      status: currentTemplate.status,
      description: currentTemplate.description,
      margin_in: currentTemplate.margin_in,
      elements: currentTemplate.elements,
    });
    setTemplate(saved);
    toast("Template saved", "success");
  }

  return (
    <>
      <div className="row" style={{ marginBottom: 12, justifyContent: "space-between" }}>
        <div className="row">
          <BackLink href="/templates" />
          <strong>{currentTemplate.name}</strong>
          <Badge value={currentTemplate.status} />
        </div>
        <div className="row">
          <button className="btn secondary small" onClick={() => setZoom((value) => Math.max(0.5, +(value - 0.1).toFixed(2)))}>−</button>
          <span className="muted">{Math.round(zoom * 100)}%</span>
          <button className="btn secondary small" onClick={() => setZoom((value) => Math.min(1.6, +(value + 0.1).toFixed(2)))}>+</button>
          <button className="btn danger small" onClick={async () => {
            await api.deleteTemplate(currentTemplate.id);
            router.push("/templates");
          }}>Delete</button>
          <button className="btn primary" onClick={save}>Save</button>
        </div>
      </div>
      <div className="editor">
        <aside className="panel">
          <h2>Toolbox</h2>
          <p className="sub">Add a block, then place it on the page.</p>
          {["Text", "Address", "Data Field", "Divider"].map((type) => (
            <button key={type} className="btn secondary tool" onClick={() => {
              const el = newElement(type);
              setTemplate({ ...currentTemplate, elements: [...currentTemplate.elements, el] });
              setSelected(el.id);
            }}>{type}</button>
          ))}
          <div className="field" style={{ marginTop: 16 }}><label>Name</label>
            <input value={currentTemplate.name} onChange={(event) => setTemplate({ ...currentTemplate, name: event.target.value })} />
          </div>
          <div className="field"><label>Status</label>
            <select value={currentTemplate.status} onChange={(event) => setTemplate({ ...currentTemplate, status: event.target.value })}>
              <option>Draft</option><option>Published</option>
            </select>
          </div>
          <p className="muted">{currentTemplate.kind} · {currentTemplate.width_in} × {currentTemplate.height_in} in</p>
        </aside>
        <DocumentCanvas
          widthIn={currentTemplate.width_in}
          heightIn={currentTemplate.height_in}
          marginIn={currentTemplate.margin_in}
          elements={currentTemplate.elements}
          selectedId={selected}
          zoom={zoom}
          showGrid
          editable
          onSelect={setSelected}
          onChange={patchElement}
        />
        <aside className="panel stack">
          <h2>Inspector</h2>
          {current ? (
            <>
              <div className="field"><label>Name</label><input value={current.name} onChange={(event) => patchElement(current.id, { name: event.target.value })} /></div>
              <div className="field"><label>Content</label><textarea value={current.content} onChange={(event) => patchElement(current.id, { content: event.target.value })} /></div>
              <div className="field"><label>Font size</label><input type="number" value={current.font_size} onChange={(event) => patchElement(current.id, { font_size: Number(event.target.value) })} /></div>
              <label className="check"><input type="checkbox" checked={current.visible} onChange={(event) => patchElement(current.id, { visible: event.target.checked })} /> Visible</label>
              <button className="btn danger" onClick={() => setTemplate({ ...currentTemplate, elements: currentTemplate.elements.filter((el) => el.id !== current.id) })}>Remove block</button>
            </>
          ) : <p className="secondary">Select a block to edit it. Drag blocks to reposition them.</p>}
        </aside>
      </div>
    </>
  );
}
