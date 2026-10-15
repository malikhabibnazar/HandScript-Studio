"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { formatBytes } from "@/lib/format";
import type { Profile, Settings, Template } from "@/lib/types";

const CATS = ["General", "Appearance", "Generation", "Storage", "Printing", "About"];

export default function SettingsPage() {
  const toast = useToast();
  const [cat, setCat] = useState("General");
  const [settings, setSettings] = useState<Settings | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);

  useEffect(() => {
    Promise.all([api.settings(), api.templates(), api.profiles()]).then(([next, nextTemplates, nextProfiles]) => {
      setSettings(next);
      setTemplates(nextTemplates);
      setProfiles(nextProfiles);
      if (next.theme === "dark" || next.theme === "light") {
        document.documentElement.dataset.theme = next.theme;
        localStorage.setItem("hs-theme", next.theme);
      }
    }).catch((err: Error) => toast(err.message, "danger"));
  }, [toast]);

  if (!settings) return <div className="loading">Loading settings…</div>;

  async function save(patch: Partial<Settings>) {
    const next = await api.saveSettings(patch);
    setSettings(next);
    if (patch.theme === "light" || patch.theme === "dark") {
      document.documentElement.dataset.theme = patch.theme;
      localStorage.setItem("hs-theme", patch.theme);
    }
    toast("Settings saved", "success");
  }

  return (
    <div className="settings-layout">
      <aside className="card">
        <h2 style={{ marginBottom: 12 }}>Settings</h2>
        <div className="stack">
          {CATS.map((item) => (
            <button key={item} className={cat === item ? "nav-item active" : "nav-item"} onClick={() => setCat(item)}>{item}</button>
          ))}
        </div>
      </aside>
      <section className="card">
        {cat === "General" ? (
          <>
            <h2>Workspace & defaults</h2>
            <Row title="Workspace" subtitle="Shown as the sender when a CSV omits one">
              <input value={settings.workspace} onChange={(event) => setSettings({ ...settings, workspace: event.target.value })} onBlur={() => save({ workspace: settings.workspace })} />
            </Row>
            <Row title="Default output folder" subtitle="Prefix used for generated files">
              <input value={settings.output_dir} onChange={(event) => setSettings({ ...settings, output_dir: event.target.value })} onBlur={() => save({ output_dir: settings.output_dir })} />
            </Row>
            <Row title="Default template">
              <select value={settings.default_template_id} onChange={(event) => save({ default_template_id: event.target.value })}>
                {templates.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </Row>
            <Row title="Default handwriting profile">
              <select value={settings.default_profile_id} onChange={(event) => save({ default_profile_id: event.target.value })}>
                {profiles.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </Row>
          </>
        ) : null}
        {cat === "Appearance" ? (
          <>
            <h2>Appearance</h2>
            <Row title="Theme" subtitle="Light or dark">
              <select value={settings.theme} onChange={(event) => save({ theme: event.target.value })}>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </select>
            </Row>
            <Row title="UI scale" subtitle="Stored with your preferences">
              <input type="number" min={80} max={140} value={settings.ui_scale} onChange={(event) => setSettings({ ...settings, ui_scale: Number(event.target.value) })} onBlur={() => save({ ui_scale: settings.ui_scale })} />
            </Row>
            <Row title="Reduce motion">
              <input type="checkbox" checked={settings.reduce_motion} onChange={(event) => save({ reduce_motion: event.target.checked })} />
            </Row>
          </>
        ) : null}
        {cat === "Generation" ? (
          <>
            <h2>Generation defaults</h2>
            <Row title="Default export format">
              <select value={settings.export_format} onChange={(event) => save({ export_format: event.target.value })}>
                <option>PDF</option><option>PNG</option><option>Combined PDF</option>
              </select>
            </Row>
            <Row title="Default resolution">
              <select value={settings.resolution} onChange={(event) => save({ resolution: event.target.value })}>
                <option>150 dpi</option><option>300 dpi</option><option>600 dpi</option>
              </select>
            </Row>
            <Row title="Pause on first error" subtitle="Stop the batch if a page fails to render">
              <input type="checkbox" checked={settings.pause_on_error} onChange={(event) => save({ pause_on_error: event.target.checked })} />
            </Row>
          </>
        ) : null}
        {cat === "Storage" ? (
          <>
            <h2>Storage</h2>
            <Row title="Cache" subtitle="Preview files kept by the renderer"><strong>{formatBytes(settings.cache_bytes)}</strong></Row>
            <Row title="Clear cache" subtitle="Generated downloads are kept">
              <button className="btn danger" onClick={async () => {
                const result = await api.clearCache();
                toast(`Freed ${formatBytes(result.freed_bytes)}`, "success");
                setSettings(await api.settings());
              }}>Clear cache</button>
            </Row>
          </>
        ) : null}
        {cat === "Printing" ? (
          <>
            <h2>Printing</h2>
            <Row title="Default printer">
              <select value={settings.printer} onChange={(event) => save({ printer: event.target.value })}>
                <option>System Default</option><option>Office LaserJet</option><option>Photo Printer</option>
              </select>
            </Row>
            <Row title="Page scaling">
              <select value={settings.page_scaling} onChange={(event) => save({ page_scaling: event.target.value })}>
                <option>Actual size</option><option>Fit to page</option><option>Shrink oversized</option>
              </select>
            </Row>
            <Row title="Print margins">
              <select value={settings.print_margins} onChange={(event) => save({ print_margins: event.target.value })}>
                <option>None</option><option>Minimal</option><option>Standard</option>
              </select>
            </Row>
          </>
        ) : null}
        {cat === "About" ? (
          <>
            <h2>HandScript Studio</h2>
            <p className="sub">Version 1.0.0 · web</p>
            <Row title="API" subtitle="FastAPI"><strong>Connected</strong></Row>
            <Row title="Rendering" subtitle="Physical page sizes"><strong>ReportLab + Pillow</strong></Row>
            <Row title="Database" subtitle="SQLite locally, PostgreSQL in Docker"><strong>SQLAlchemy</strong></Row>
          </>
        ) : null}
      </section>
    </div>
  );
}

function Row({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div className="setting-row">
      <div><strong>{title}</strong>{subtitle ? <p>{subtitle}</p> : null}</div>
      <div className="control">{children}</div>
    </div>
  );
}
