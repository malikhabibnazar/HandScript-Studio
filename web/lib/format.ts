export function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function relativeTime(value: string) {
  const date = new Date(value);
  const seconds = Math.max(0, (Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const TONES: Record<string, string> = {
  Draft: "neutral",
  Ready: "info",
  Generating: "warning",
  Processing: "warning",
  "Needs Review": "warning",
  Completed: "success",
  Published: "success",
  Failed: "danger",
  Error: "danger",
  Partial: "warning",
  Queued: "info",
  Running: "info",
  Paused: "neutral",
  Cancelled: "neutral",
  PDF: "neutral",
  PNG: "neutral",
  "Combined PDF": "neutral",
};

export function toneFor(status: string) {
  return TONES[status] || "neutral";
}
