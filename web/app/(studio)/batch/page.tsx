"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader, useToast } from "@/components/ui";
import { API_URL, api } from "@/lib/api";
import type { ImportSummary, Profile, Template } from "@/lib/types";

const STEPS = ["Template", "Handwriting", "Import Data", "Output", "Review"];

export default function BatchWizardPage() {
  const router = useRouter();
  const toast = useToast();
  const [step, setStep] = useState(0);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [templateId, setTemplateId] = useState("");
  const [profileId, setProfileId] = useState("");
  const [imported, setImported] = useState<ImportSummary | null>(null);
  const [name, setName] = useState("");
  const [format, setFormat] = useState("PDF");
  const [naming, setNaming] = useState("document_{index}");
  const [individual, setIndividual] = useState(true);
  const [combined, setCombined] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api.templates(), api.profiles()]).then(([nextTemplates, nextProfiles]) => {
      setTemplates(nextTemplates);
      setProfiles(nextProfiles);
    }).catch((err: Error) => toast(err.message, "danger"));
  }, [toast]);

  const template = templates.find((item) => item.id === templateId);
  const profile = profiles.find((item) => item.id === profileId);
  const canNext = [
    Boolean(templateId),
    Boolean(profileId),
    Boolean(imported && imported.valid_records > 0),
    individual || combined,
    true,
  ][step];

  async function start() {
    if (!imported) return;
    setBusy(true);
    try {
      const batch = await api.createBatch({
        name: name || imported.filename,
        template_id: templateId,
        profile_id: profileId,
        import_id: imported.id,
        export_format: format,
        naming,
        individual,
        combined,
      });
      router.push(`/batch/${batch.id}`);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not start the batch", "danger");
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Batch Generator" subtitle="Generate documents for an entire data list in five steps." />
      <div className="stepper">
        {STEPS.map((label, index) => <div key={label} className={index === step ? "step on" : index < step ? "step done" : "step"}>{index + 1}. {label}</div>)}
      </div>
      <section className="card">
        {step === 0 ? (
          <div className="stack">
            <h2>Select a template</h2>
            {templates.map((item) => (
              <button key={item.id} className={templateId === item.id ? "option on" : "option"} onClick={() => setTemplateId(item.id)}>
                <div style={{ flex: 1 }}><strong>{item.name}</strong><div className="muted">{item.kind} · {item.width_in} × {item.height_in} in</div></div>
                <i className="radio" />
              </button>
            ))}
          </div>
        ) : null}
        {step === 1 ? (
          <div className="stack">
            <h2>Select a handwriting profile</h2>
            <p className="sub">Only ready profiles can be used.</p>
            {profiles.map((item) => (
              <button key={item.id} disabled={item.status !== "Ready"} className={profileId === item.id ? "option on" : "option"} onClick={() => setProfileId(item.id)}>
                <div style={{ flex: 1 }}><strong>{item.name}</strong><div className="muted">{item.sample_count} samples · {item.status}</div></div>
                <i className="radio" />
              </button>
            ))}
          </div>
        ) : null}
        {step === 2 ? (
          <div className="stack">
            <h2>Import data</h2>
            <p className="sub">
              Upload the codes to print. A .txt file has one code per line. A .csv file has a code column.
              Each valid code is printed on its own card where the template says {"{code}"}. Codes stay text, so leading zeros are kept.
              A code that appears twice is printed twice. A blank line is reported and skipped.
            </p>
            <div className="row">
              <a className="btn secondary" href={`${API_URL}/api/imports/samples/codes.csv`} download="codes.csv">Download example CSV</a>
              <a className="btn secondary" href={`${API_URL}/api/imports/samples/codes.txt`} download="codes.txt">Download example TXT</a>
            </div>
            <label className="btn secondary" style={{ width: "fit-content" }}>
              Choose CSV or TXT
              <input hidden type="file" accept=".csv,.txt,text/csv,text/plain" onChange={async (event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                if (!file) return;
                try {
                  const summary = await api.uploadImport(file);
                  setImported(summary);
                  if (!name) setName(file.name.replace(/\.(csv|txt)$/i, ""));
                } catch (err) {
                  toast(err instanceof Error ? err.message : "Import failed", "danger");
                }
              }} />
            </label>
            {imported ? (
              <>
                <p>{imported.filename}: {imported.valid_records} valid, {imported.invalid_records} flagged, {imported.records_detected} detected.</p>
                <div className="table-wrap">
                  <table>
                    <thead><tr>{imported.columns.map((col) => <th key={col}>{col}</th>)}</tr></thead>
                    <tbody>
                      {imported.rows.map((row, index) => <tr key={index}>{imported.columns.map((col) => <td key={col}>{row[col]}</td>)}</tr>)}
                    </tbody>
                  </table>
                </div>
                {imported.issues.length ? (
                  <div className="stack">
                    {imported.issues.map((issue) => <p key={`${issue.line}-${issue.reason}`} className="secondary">Line {issue.line}: {issue.reason}</p>)}
                  </div>
                ) : null}
              </>
            ) : null}
          </div>
        ) : null}
        {step === 3 ? (
          <div className="stack">
            <h2>Output</h2>
            <div className="field"><label>Batch name</label><input value={name} onChange={(event) => setName(event.target.value)} /></div>
            <div className="field"><label>Format</label>
              <select value={format} onChange={(event) => setFormat(event.target.value)}>
                <option>PDF</option><option>PNG</option><option>Combined PDF</option>
              </select>
            </div>
            <div className="field"><label>File naming</label><input value={naming} onChange={(event) => setNaming(event.target.value)} /></div>
            <label className="check"><input type="checkbox" checked={individual} onChange={(event) => setIndividual(event.target.checked)} /> Individual files</label>
            <label className="check"><input type="checkbox" checked={combined} onChange={(event) => setCombined(event.target.checked)} /> Combined PDF</label>
          </div>
        ) : null}
        {step === 4 ? (
          <div className="stack">
            <h2>Review</h2>
            <div className="setting-row"><span>Template</span><strong>{template?.name}</strong></div>
            <div className="setting-row"><span>Profile</span><strong>{profile?.name}</strong></div>
            <div className="setting-row"><span>Records</span><strong>{imported?.valid_records} valid / {imported?.records_detected} total</strong></div>
            <div className="setting-row"><span>Output</span><strong>{format} · {naming}</strong></div>
          </div>
        ) : null}
      </section>
      <div className="row" style={{ marginTop: 16, justifyContent: "space-between" }}>
        <button className="btn secondary" disabled={step === 0} onClick={() => setStep((value) => value - 1)}>Back</button>
        {step < 4
          ? <button className="btn primary" disabled={!canNext} onClick={() => setStep((value) => value + 1)}>Continue</button>
          : <button className="btn primary" disabled={busy || !canNext} onClick={start}>{busy ? "Starting…" : "Generate"}</button>}
      </div>
    </>
  );
}
