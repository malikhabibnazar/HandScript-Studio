"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Badge, useToast } from "@/components/ui";
import { API_URL, api, downloadExport } from "@/lib/api";
import type { Batch, ExportRecord } from "@/lib/types";

export default function BatchProgressPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const [batch, setBatch] = useState<Batch | null>(null);
  const [exportRow, setExportRow] = useState<ExportRecord | null>(null);

  useEffect(() => {
    api.batch(params.id).then(setBatch).catch((err: Error) => toast(err.message, "danger"));
    const source = new EventSource(`${API_URL}/api/batches/${params.id}/events`);
    source.onmessage = (event) => setBatch(JSON.parse(event.data));
    source.onerror = () => source.close();
    return () => source.close();
  }, [params.id, toast]);

  useEffect(() => {
    if (!batch || !["Completed", "Failed"].includes(batch.status)) return;
    api.exports().then((rows) => {
      setExportRow(rows.find((row) => row.batch_id === batch.id) || null);
    }).catch(() => undefined);
  }, [batch?.status, batch?.id]);

  if (!batch) return <div className="loading">Loading batch…</div>;
  const percent = Math.round((batch.progress || 0) * 100);
  const done = ["Completed", "Failed", "Cancelled"].includes(batch.status);

  return (
    <div className="stack" style={{ maxWidth: 720, margin: "0 auto" }}>
      <button className="btn ghost" onClick={() => router.push("/batch")}>Batch Generator</button>
      <section className="card" style={{ textAlign: "center" }}>
        <Badge value={batch.status} />
        <h1 style={{ fontSize: 24, margin: "12px 0 6px" }}>{done && batch.status === "Completed" ? "Generation complete" : batch.name}</h1>
        <p className="secondary">{batch.template_name} · {batch.profile_name}</p>
        <svg className="progress-ring" viewBox="0 0 120 120" style={{ margin: "18px auto", display: "block" }}>
          <circle cx="60" cy="60" r="52" fill="none" stroke="var(--divider)" strokeWidth="8" />
          <circle cx="60" cy="60" r="52" fill="none" stroke="var(--accent)" strokeWidth="8"
            strokeDasharray={`${percent * 3.27} 327`} strokeLinecap="round" transform="rotate(-90 60 60)" />
          <text x="60" y="66" textAnchor="middle" fontSize="22" fill="var(--text)" fontFamily="Segoe UI, sans-serif">{percent}%</text>
        </svg>
        <p>{batch.generated.toLocaleString()} generated · {batch.failed.toLocaleString()} failed · {batch.total.toLocaleString()} total</p>
        <p className="muted" style={{ marginTop: 6 }}>{
          done && exportRow?.filename
            ? `Saved to Exports · ${exportRow.filename}`
            : batch.current_item || batch.error || (done ? "Finished" : "Waiting for the worker")
        }</p>
        <div className="meter" style={{ marginTop: 16 }}><span style={{ width: `${percent}%` }} /></div>
      </section>
      <div className="row" style={{ justifyContent: "center" }}>
        {batch.runnable && (batch.status === "Running" || batch.status === "Queued") ? (
          <button className="btn secondary" onClick={async () => setBatch(await api.pauseBatch(batch.id))}>Pause</button>
        ) : null}
        {batch.runnable && batch.status === "Paused" ? (
          <button className="btn primary" onClick={async () => setBatch(await api.resumeBatch(batch.id))}>Resume</button>
        ) : null}
        {batch.runnable && !done ? (
          <button className="btn danger" onClick={async () => setBatch(await api.cancelBatch(batch.id))}>Cancel</button>
        ) : null}
        {exportRow?.has_file ? (
          <button className="btn primary" onClick={() => {
            if (!exportRow) return;
            downloadExport(exportRow.id);
            toast("Download started", "success");
          }}>Download</button>
        ) : null}
        {done ? <button className="btn secondary" onClick={() => router.push("/exports")}>View in Exports</button> : null}
      </div>
      {!batch.runnable ? <p className="muted" style={{ textAlign: "center" }}>This entry is from the sample history. Start a new batch to render files.</p> : null}
    </div>
  );
}
