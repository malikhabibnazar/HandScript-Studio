"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/icons";
import { PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.dashboard().then(setData).catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <div className="empty"><h3>Studio API is not reachable</h3><p>{error}</p></div>;
  if (!data) return <div className="loading">Loading your workspace…</div>;

  const cards = [
    ["Handwriting Profiles", data.counts.profiles, "handwriting", ""],
    ["Templates", data.counts.templates, "templates", "neutral"],
    ["Documents Generated", data.counts.documents_generated, "documents", "success"],
    ["Batches", data.counts.recent_batches, "batch", "warning"],
  ] as const;

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Generate printable documents from editable templates and your handwriting styles.">
        <button className="btn secondary" onClick={() => router.push("/batch")}><Icon name="batch" size={16} /> Start Batch</button>
        <button className="btn primary" onClick={() => router.push("/documents")}><Icon name="plus" size={16} /> Create Document</button>
      </PageHeader>
      <div className="grid-4">
        {cards.map(([label, value, icon, tone]) => (
          <div className="card stat" key={label}>
            <div className={`icon-bubble ${tone}`}><Icon name={icon} /></div>
            <div>
              <div className="label">{label}</div>
              <div className="value">{value.toLocaleString()}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="grid-2">
        <section className="card">
          <h2>Recent activity</h2>
          <p className="sub">Across documents, templates and imports</p>
          {data.activity.map((item) => (
            <div className="activity" key={item.id}>
              <div className="icon-bubble neutral"><Icon name={item.kind === "error" ? "batch" : item.kind === "import" ? "exports" : item.kind} size={16} /></div>
              <div style={{ flex: 1 }}>
                <strong>{item.title}</strong>
                <div className="muted">{item.detail}</div>
              </div>
              <span className="muted">{relativeTime(item.when)}</span>
            </div>
          ))}
        </section>
        <div className="stack">
          <section className="card">
            <h2>Quick actions</h2>
            <p className="sub">Common next steps</p>
            <div className="stack">
              <Link className="option" href="/documents">New document from a template</Link>
              <Link className="option" href="/handwriting">Review handwriting profiles</Link>
              <Link className="option" href="/batch">Import a CSV and generate</Link>
            </div>
          </section>
          <section className="card">
            <h2>System</h2>
            <p className="sub">Services behind this studio</p>
            {Object.entries(data.system).map(([key, value]) => (
              <div className="setting-row" key={key}><span className="secondary">{key}</span><strong>{value}</strong></div>
            ))}
          </section>
        </div>
      </div>
    </>
  );
}
