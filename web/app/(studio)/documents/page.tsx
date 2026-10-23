"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BackLink, Badge, Empty, Modal, PageHeader, useConfirm, useToast } from "@/components/ui";
import { Icon } from "@/components/icons";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { DocumentItem, Profile, Template } from "@/lib/types";

const FILTERS = ["Draft", "Ready", "Generating", "Completed", "Failed"];

export default function DocumentsPage() {
  const router = useRouter();
  const toast = useToast();
  const [rows, setRows] = useState<DocumentItem[] | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [templateId, setTemplateId] = useState("");
  const [profileId, setProfileId] = useState("");
  const [name, setName] = useState("");
  const { confirm, dialog } = useConfirm();

  function load(nextQuery = query, nextStatus = status) {
    api.documents(nextQuery, nextStatus).then(setRows).catch((err: Error) => toast(err.message, "danger"));
  }

  useEffect(() => { load(); }, []);

  async function create() {
    const doc = await api.createDocument({ name: name || undefined, template_id: templateId, profile_id: profileId || undefined });
    router.push(`/documents/${doc.id}`);
  }

  function openCreate() {
    Promise.all([api.templates(), api.profiles()]).then(([nextTemplates, nextProfiles]) => {
      setTemplates(nextTemplates);
      setProfiles(nextProfiles);
      setTemplateId(nextTemplates[0]?.id || "");
      setProfileId(nextProfiles.find((item) => item.is_default)?.id || nextProfiles[0]?.id || "");
      setOpen(true);
    }).catch((err: Error) => toast(err.message, "danger"));
  }

  async function removeDocument(row: DocumentItem) {
    const deleted = await confirm({
      title: "Delete document?",
      message: `"${row.name}" will be permanently removed. This cannot be undone.`,
      confirmLabel: "Delete document",
      action: () => api.deleteDocument(row.id),
    });
    if (!deleted) return;
    setSelected((current) => current.filter((id) => id !== row.id));
    toast("Document deleted", "success");
    setRows((current) => current?.filter((item) => item.id !== row.id) ?? current);
  }

  async function removeSelected() {
    const ids = selected;
    const picked = (rows ?? []).filter((row) => ids.includes(row.id));
    const count = ids.length;
    const message = count === 1 && picked.length === 1
      ? `"${picked[0].name}" will be permanently removed. This cannot be undone.`
      : `${count} documents will be permanently removed. This cannot be undone.`;
    const deleted = await confirm({
      title: count === 1 ? "Delete document?" : "Delete documents?",
      message,
      confirmLabel: count === 1 ? "Delete document" : "Delete documents",
      action: () => api.bulkDeleteDocuments(ids),
    });
    if (!deleted) return;
    setSelected([]);
    toast(count === 1 ? "Document deleted" : "Documents deleted", "success");
    load();
  }

  if (!rows) return <><div className="page-back"><BackLink href="/dashboard" /></div><div className="loading">Loading documents…</div></>;

  return (
    <>
      {dialog}
      <div className="page-back"><BackLink href="/dashboard" /></div>
      <PageHeader title="Documents" subtitle="Create, organise and export your documents.">
        <button className="btn secondary" onClick={() => router.push("/batch")}><Icon name="exports" size={16} /> Import</button>
        <button className="btn primary" onClick={openCreate}><Icon name="plus" size={16} /> Create Document</button>
      </PageHeader>
      <div className="row" style={{ marginBottom: 8 }}>
        <input className="search" placeholder="Search documents…" value={query} onChange={(event) => {
          setQuery(event.target.value);
          load(event.target.value, status);
        }} />
      </div>
      <div className="filters">
        <button className={status === "" ? "chip on" : "chip"} onClick={() => { setStatus(""); load(query, ""); }}>All</button>
        {FILTERS.map((item) => (
          <button key={item} className={status === item ? "chip on" : "chip"} onClick={() => { setStatus(item); load(query, item); }}>{item}</button>
        ))}
      </div>
      {selected.length > 0 ? (
        <div className="row" style={{ marginBottom: 10 }}>
          <span className="secondary">{selected.length} selected</span>
          <button className="btn danger small" type="button" onClick={() => { void removeSelected(); }}>Delete</button>
        </div>
      ) : null}
      {rows.length === 0 ? (
        <Empty title="No documents yet" body="Create a document from a template, or import a CSV to generate in bulk." action={<button className="btn primary" onClick={openCreate}>Create Document</button>} />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th /><th>Name</th><th>Template</th><th>Profile</th><th>Status</th><th>Format</th><th>Modified</th><th /></tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td><input type="checkbox" checked={selected.includes(row.id)} onChange={(event) => {
                    setSelected((current) => event.target.checked ? [...current, row.id] : current.filter((id) => id !== row.id));
                  }} /></td>
                  <td><button className="btn ghost" onClick={() => router.push(`/documents/${row.id}`)}>{row.name}</button></td>
                  <td>{row.template_name}</td>
                  <td>{row.profile_name}</td>
                  <td><Badge value={row.status} /></td>
                  <td>{row.export_format}</td>
                  <td>{formatDate(row.modified)}</td>
                  <td className="row-actions">
                    <div className="row">
                      <button className="btn ghost small" type="button" onClick={async () => {
                        const copy = await api.duplicateDocument(row.id);
                        toast("Document duplicated", "success");
                        router.push(`/documents/${copy.id}`);
                      }}>Duplicate</button>
                      <button className="btn danger small" type="button" aria-label={`Delete ${row.name}`} onClick={() => { void removeDocument(row); }}>
                        <Icon name="trash" size={14} />
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {open ? (
        <Modal title="New document" onClose={() => setOpen(false)}>
          <div className="stack" style={{ marginTop: 14 }}>
            <div className="field"><label>Name</label><input value={name} placeholder="Optional" onChange={(event) => setName(event.target.value)} /></div>
            <div className="field"><label>Template</label>
              <select value={templateId} onChange={(event) => setTemplateId(event.target.value)}>
                {templates.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </div>
            <div className="field"><label>Handwriting profile</label>
              <select value={profileId} onChange={(event) => setProfileId(event.target.value)}>
                {profiles.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </div>
            <div className="row" style={{ justifyContent: "flex-end" }}>
              <button className="btn ghost" onClick={() => setOpen(false)}>Cancel</button>
              <button className="btn primary" disabled={!templateId} onClick={create}>Create</button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
