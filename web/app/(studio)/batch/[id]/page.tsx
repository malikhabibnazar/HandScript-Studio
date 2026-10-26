"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Badge, useToast } from "@/components/ui";
import { api, downloadExport, previewExport, printExport } from "@/lib/api";
import type { Batch, ExportRecord } from "@/lib/types";

export default function BatchProgressPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const [batch, setBatch] = useState<Batch | null>(null);
  const [exportRow, setExportRow] = useState<ExportRecord | null>(null);
  const [printing, setPrinting] = useState(false);

  useEffect(() => {
    let stopped = false;
    let timer = 0;
    let seen = false;
    const finished = (status: string) => ["Completed", "Failed", "Cancelled"].includes(status);
    const pull = async () => {
      try {
        const next = await api.batch(params.id);
        if (stopped) return;
        seen = true;
        setBatch(next);
        if (finished(next.status)) {
          const rows = await api.exports();
          if (!stopped) setExportRow(rows.find((row) => row.batch_id === next.id) || null);
          return;
        }
      } catch (err) {
        if (!stopped && !seen) toast(err instanceof Error ? err.message : "Could not load the batch", "danger");
      }
      if (!stopped) timer = window.setTimeout(pull, 1000);
    };
    void pull();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
    };
  }, [params.id, toast]);

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
          <>
            <button className="btn primary" onClick={() => {
              if (!exportRow) return;
              downloadExport(exportRow.id);
              toast("Download started", "success");
            }}>Download</button>
            <button className="btn secondary" disabled={printing} onClick={async () => {
              if (!exportRow) return;
              setPrinting(true);
              try {
                await printExport(exportRow.id, exportRow.filename);
              } catch (err) {
                toast(err instanceof Error ? err.message : "Could not print", "danger");
              } finally {
                setPrinting(false);
              }
            }}>{printing ? "Printing…" : "Print"}</button>
            <button className="btn secondary" type="button" onClick={() => {
              if (!exportRow) return;
              try {
                previewExport(exportRow.id, exportRow.filename);
              } catch (err) {
                toast(err instanceof Error ? err.message : "Could not open the preview", "danger");
              }
            }}>Preview</button>
          </>
        ) : null}
        {done ? <button className="btn secondary" onClick={() => router.push("/exports")}>View in Exports</button> : null}
      </div>
      {!batch.runnable ? <p className="muted" style={{ textAlign: "center" }}>This entry is from the sample history. Start a new batch to render files.</p> : null}
    </div>
  );
}
