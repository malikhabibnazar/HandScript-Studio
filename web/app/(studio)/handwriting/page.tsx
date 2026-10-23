"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BackLink, Badge, Empty, Modal, PageHeader, useConfirm, useToast } from "@/components/ui";
import { Icon } from "@/components/icons";
import { api } from "@/lib/api";
import type { Profile } from "@/lib/types";
import { ENGINE_LABEL } from "@/components/renderer-choice";

export default function HandwritingPage() {
  const router = useRouter();
  const toast = useToast();
  const [rows, setRows] = useState<Profile[] | null>(null);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const { confirm, dialog } = useConfirm();

  function load() {
    api.profiles().then(setRows).catch((err: Error) => toast(err.message, "danger"));
  }
  useEffect(() => {
    load();
  }, []);

  async function remove(item: Profile) {
    const deleted = await confirm({
      title: "Delete profile?",
      message: `"${item.name}" and its samples will be permanently removed. This cannot be undone.`,
      confirmLabel: "Delete profile",
      action: () => api.deleteProfile(item.id),
    });
    if (!deleted) return;
    toast("Profile deleted", "success");
    setRows((current) => current?.filter((row) => row.id !== item.id) ?? current);
  }

  if (!rows) return <><div className="page-back"><BackLink href="/dashboard" /></div><div className="loading">Loading profiles…</div></>;

  return (
    <>
      {dialog}
      <div className="page-back"><BackLink href="/dashboard" /></div>
      <PageHeader title="Handwriting" subtitle="Profiles are made from a handwriting photo with HandFonted.">
        <button className="btn primary" onClick={() => setOpen(true)}><Icon name="plus" size={16} /> New Profile</button>
      </PageHeader>
      {rows.length === 0 ? <Empty title="No profiles" body="Create a profile, then upload a photo of the alphabet." /> : (
        <div className="cards">
          {rows.map((item) => (
            <article key={item.id} className="card profile-card">
              <button type="button" className="profile-open" onClick={() => router.push(`/handwriting/${item.id}`)}>
                <p className="hand">{item.preview_text}</p>
                <div className="row" style={{ justifyContent: "space-between", marginTop: 12 }}>
                  <strong>{item.name}</strong>
                  <Badge value={item.status} />
                </div>
                {item.is_default ? <p className="muted">Default profile</p> : null}
                <p className="muted" style={{ marginTop: 6 }}>{item.style?.engine === "drawn" ? "Drawn letters" : `${item.sample_count} samples · ${ENGINE_LABEL[item.style?.engine ?? "graves"]}`}</p>
                <p className="secondary" style={{ marginTop: 8 }}>{item.description}</p>
              </button>
              <div className="profile-actions">
                <button type="button" className="btn danger small" aria-label={`Delete ${item.name}`} onClick={() => { void remove(item); }}>
                  <Icon name="trash" size={14} />
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
      {open ? (
        <Modal title="New handwriting profile" onClose={() => setOpen(false)}>
          <div className="stack" style={{ marginTop: 14 }}>
            <div className="field">
              <label htmlFor="profile-name">Name</label>
              <input id="profile-name" value={name} onChange={(event) => setName(event.target.value)} />
            </div>
            <div className="field">
              <label>Renderer</label>
              <div className="option on" aria-disabled="true" style={{ cursor: "default" }}>
                <span className="radio" />
                <strong>HandFonted</strong>
              </div>
            </div>
            <div className="row" style={{ justifyContent: "flex-end" }}>
              <button className="btn ghost" disabled={creating} onClick={() => setOpen(false)}>Cancel</button>
              <button className="btn primary" disabled={!name.trim() || creating} onClick={async () => {
                setCreating(true);
                try {
                  const created = await api.createProfile({ name: name.trim(), engine: "handfonted" });
                  router.push(`/handwriting/${created.id}`);
                } catch (err) {
                  toast(err instanceof Error ? err.message : "Could not create the profile", "danger");
                  setCreating(false);
                }
              }}>{creating ? "Creating…" : "Create"}</button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
