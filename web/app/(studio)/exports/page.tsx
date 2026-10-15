"use client";

import { useEffect, useState } from "react";
import { Badge, Empty, PageHeader, useToast } from "@/components/ui";
import { api, downloadExport } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { ExportRecord } from "@/lib/types";

export default function ExportsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<ExportRecord[] | null>(null);
  const [status, setStatus] = useState("");

  function load() {
    api.exports().then(setRows).catch((err: Error) => toast(err.message, "danger"));
  }
  useEffect(() => { load(); }, []);
  if (!rows) return <div className="loading">Loading exports…</div>;
  const visible = status ? rows.filter((row) => row.status === status) : rows;

  return (
    <>
      <PageHeader title="Exports" subtitle="Files produced by batch generation." />
      <div className="filters">
        {["", "Completed", "Partial", "Failed"].map((item) => (
          <button key={item || "all"} className={status === item ? "chip on" : "chip"} onClick={() => setStatus(item)}>{item || "All"}</button>
        ))}
      </div>
      {visible.length === 0 ? <Empty title="No exports" body="Finished batches appear here with a download." /> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Batch</th><th>Date</th><th>Files</th><th>Format</th><th>Status</th><th>Size</th><th /></tr></thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.id}>
                  <td>{row.batch_name}</td>
                  <td>{formatDate(row.date)}</td>
                  <td>{row.file_count.toLocaleString()}</td>
                  <td>{row.format}</td>
                  <td><Badge value={row.status} /></td>
                  <td>{row.size_mb.toFixed(1)} MB</td>
                  <td className="row">
                    <button className="btn ghost small" disabled={!row.has_file} onClick={() => downloadExport(row.id)}>Download</button>
                    <button className="btn danger small" onClick={async () => {
                      await api.deleteExport(row.id);
                      toast("Export removed", "success");
                      load();
                    }}>Delete</button>
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
