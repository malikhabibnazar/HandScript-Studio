"use client";

import { useEffect, useState } from "react";
import { Badge, Empty, PageHeader, useConfirm, useToast } from "@/components/ui";
import { api, downloadExport, printExport } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { ExportRecord } from "@/lib/types";

export default function ExportsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<ExportRecord[] | null>(null);
  const [status, setStatus] = useState("");
  const [printingId, setPrintingId] = useState("");
  const { confirm, dialog } = useConfirm();

  function load() {
    api.exports().then(setRows).catch((err: Error) => toast(err.message, "danger"));
  }
  useEffect(() => { load(); }, []);
  async function removeExport(row: ExportRecord) {
    const label = row.filename || row.batch_name;
    const deleted = await confirm({
      title: "Delete export?",
      message: `"${label}" and its files will be permanently removed. This cannot be undone.`,
      confirmLabel: "Delete export",
      action: () => api.deleteExport(row.id),
    });
    if (!deleted) return;
    toast("Export removed", "success");
    load();
  }

  if (!rows) return <div className="loading">Loading exports…</div>;
  const visible = status ? rows.filter((row) => row.status === status) : rows;

  return (
    <>
      {dialog}
      <PageHeader title="Exports" subtitle="Files produced by batch generation." />
      <div className="filters">
        {["", "Completed", "Partial", "Failed"].map((item) => (
          <button key={item || "all"} className={status === item ? "chip on" : "chip"} onClick={() => setStatus(item)}>{item || "All"}</button>
        ))}
      </div>
      {visible.length === 0 ? <Empty title="No exports" body="Finished batches appear here with a download." /> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Batch</th><th>File</th><th>Date</th><th>Files</th><th>Format</th><th>Status</th><th>Size</th><th /></tr></thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.id}>
                  <td>{row.batch_name}</td>
                  <td>{row.filename}</td>
                  <td>{formatDate(row.date)}</td>
                  <td>{row.file_count.toLocaleString()}</td>
                  <td>{row.format}</td>
                  <td><Badge value={row.status} /></td>
                  <td>{row.size_mb.toFixed(1)} MB</td>
                  <td className="row">
                    <button className="btn ghost small" disabled={!row.has_file} onClick={() => downloadExport(row.id)}>Download</button>
                    <button className="btn ghost small" disabled={!row.has_file || printingId === row.id} onClick={async () => {
                      setPrintingId(row.id);
                      try {
                        await printExport(row.id, row.filename);
                      } catch (err) {
                        toast(err instanceof Error ? err.message : "Could not print", "danger");
                      } finally {
                        setPrintingId("");
                      }
                    }}>{printingId === row.id ? "Printing…" : "Print"}</button>
                    <button className="btn danger small" type="button" onClick={() => { void removeExport(row); }}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
