"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge, Empty, Modal, PageHeader, useToast } from "@/components/ui";
import { Icon } from "@/components/icons";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Template } from "@/lib/types";

export default function TemplatesPage() {
  const router = useRouter();
  const toast = useToast();
  const [rows, setRows] = useState<Template[] | null>(null);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [kind, setKind] = useState("4×6 Card");

  function load() {
    api.templates().then(setRows).catch((err: Error) => toast(err.message, "danger"));
  }
  useEffect(() => { load(); }, []);

  if (!rows) return <div className="loading">Loading templates…</div>;

  return (
    <>
      <PageHeader title="Templates" subtitle="4×6 cards and #10 envelopes. Open one to edit the layout.">
        <button className="btn primary" onClick={() => setOpen(true)}><Icon name="plus" size={16} /> New Template</button>
      </PageHeader>
      {rows.length === 0 ? <Empty title="No templates" body="Create a card or envelope layout to start." /> : (
        <div className="cards">
          {rows.map((item) => (
            <div key={item.id} className="card preview-card" onClick={() => router.push(`/templates/${item.id}`)}>
              <div className={item.kind.includes("Envelope") ? "paper-mini envelope" : "paper-mini"}>
                <p>{item.elements.find((el) => el.type !== "Divider")?.content || item.name}</p>
              </div>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <strong>{item.name}</strong>
                <Badge value={item.status} />
              </div>
              <p className="muted" style={{ marginTop: 6 }}>{item.kind} · {item.width_in} × {item.height_in} in</p>
              <p className="muted">{formatDate(item.modified)}</p>
              <div className="row" style={{ marginTop: 8 }}>
                <span className="btn ghost small" onClick={async (event) => {
                  event.stopPropagation();
                  const copy = await api.duplicateTemplate(item.id);
                  toast("Template duplicated", "success");
                  router.push(`/templates/${copy.id}`);
                }}>Duplicate</span>
              </div>
            </div>
          ))}
        </div>
      )}
      {open ? (
        <Modal title="New template" onClose={() => setOpen(false)}>
          <div className="stack" style={{ marginTop: 14 }}>
            <div className="field"><label>Name</label><input value={name} onChange={(event) => setName(event.target.value)} /></div>
            <div className="field"><label>Kind</label>
              <select value={kind} onChange={(event) => setKind(event.target.value)}>
                <option>4×6 Card</option>
                <option>#10 Envelope</option>
              </select>
            </div>
            <div className="row" style={{ justifyContent: "flex-end" }}>
              <button className="btn primary" onClick={async () => {
                const created = await api.createTemplate({ name: name || "Untitled template", kind });
                router.push(`/templates/${created.id}`);
              }}>Create</button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
