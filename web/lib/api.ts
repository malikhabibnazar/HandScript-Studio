import type {
  Batch,
  Dashboard,
  DocumentDetail,
  DocumentItem,
  ExportRecord,
  ImportSummary,
  GlyphInventory,
  GlyphSetName,
  HandwritingEngineName,
  HandwritingStatus,
  HandfontedGlyph,
  PillowFace,
  Profile,
  Settings,
  Template,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    const text = await response.text();
    let detail = "Request failed";
    try {
      const data = text ? JSON.parse(text) : null;
      if (typeof data?.detail === "string") detail = data.detail;
    } catch {
      detail = text || detail;
    }
    throw new Error(detail);
  }
  return response.blob();
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  return data as T;
}

export const api = {
  health: () => request<Record<string, string>>("/api/health"),
  dashboard: () => request<Dashboard>("/api/dashboard"),
  settings: () => request<Settings>("/api/settings"),
  saveSettings: (body: Partial<Settings>) =>
    request<Settings>("/api/settings", { method: "PUT", body: JSON.stringify(body) }),
  clearCache: () => request<{ freed_bytes: number }>("/api/settings/clear-cache", { method: "POST" }),

  handwritingStatus: () => request<HandwritingStatus>("/api/handwriting/status"),
  profiles: () => request<Profile[]>("/api/profiles"),
  profile: (id: string) => request<Profile>(`/api/profiles/${id}`),
  createProfile: (body: { name: string; description?: string; engine?: HandwritingEngineName; font_family?: PillowFace }) =>
    request<Profile>("/api/profiles", { method: "POST", body: JSON.stringify(body) }),
  updateProfile: (id: string, body: Partial<Profile>) =>
    request<Profile>(`/api/profiles/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteProfile: (id: string) => request<void>(`/api/profiles/${id}`, { method: "DELETE" }),
  defaultProfile: (id: string) => request<Profile>(`/api/profiles/${id}/default`, { method: "POST" }),
  analyzeProfile: (id: string) => request<Profile>(`/api/profiles/${id}/analyze`, { method: "POST" }),
  uploadSample: (id: string, file: File) => {
    const body = new FormData();
    body.set("file", file);
    return request<Profile>(`/api/profiles/${id}/samples`, { method: "POST", body });
  },
  glyphs: (id: string) => request<GlyphInventory>(`/api/profiles/${id}/glyphs`),
  saveGlyph: (id: string, setName: GlyphSetName, key: string, file: Blob, metrics: {
    baselineY: number; padWidth: number; padHeight: number; cropLeft: number; cropTop: number;
  }) => {
    const body = new FormData();
    body.set("file", file, `${key}.png`);
    body.set("baseline_y", String(metrics.baselineY));
    body.set("pad_width", String(metrics.padWidth));
    body.set("pad_height", String(metrics.padHeight));
    body.set("crop_left", String(metrics.cropLeft));
    body.set("crop_top", String(metrics.cropTop));
    return request<GlyphInventory>(`/api/profiles/${id}/glyphs/${setName}/${encodeURIComponent(key)}`, { method: "PUT", body });
  },
  deleteGlyph: (id: string, setName: GlyphSetName, key: string) =>
    request<GlyphInventory>(`/api/profiles/${id}/glyphs/${setName}/${encodeURIComponent(key)}`, { method: "DELETE" }),
  restoreGlyphs: (id: string) => request<GlyphInventory>(`/api/profiles/${id}/glyphs/restore-sample`, { method: "POST" }),
  clearGlyphs: (id: string) => request<GlyphInventory>(`/api/profiles/${id}/glyphs`, { method: "DELETE" }),
  previewDrawing: async (id: string, text: string) => {
    const response = await fetch(`${API_URL}/api/profiles/${id}/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
      cache: "no-store",
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || "Preview failed");
    }
    return response.blob();
  },
  processHandfonted: (id: string, file: File) => {
    const body = new FormData();
    body.set("file", file);
    return request<Profile>(`/api/profiles/${id}/handfonted/process`, { method: "POST", body });
  },
  saveHandfontedGlyphs: (id: string, glyphs: HandfontedGlyph[], thickness: number) =>
    request<Profile>(`/api/profiles/${id}/handfonted/glyphs`, {
      method: "PUT",
      body: JSON.stringify({ glyphs, thickness }),
    }),
  generateHandfonted: (id: string, glyphs: HandfontedGlyph[], thickness: number) =>
    request<Profile>(`/api/profiles/${id}/handfonted/generate`, {
      method: "POST",
      body: JSON.stringify({ glyphs, thickness }),
    }),
  previewHandfonted: (id: string, text: string) =>
    requestBlob(`/api/profiles/${id}/handfonted/preview`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  templates: () => request<Template[]>("/api/templates"),
  template: (id: string) => request<Template>(`/api/templates/${id}`),
  createTemplate: (body: { name: string; kind: string; description?: string }) =>
    request<Template>("/api/templates", { method: "POST", body: JSON.stringify(body) }),
  updateTemplate: (id: string, body: Partial<Template>) =>
    request<Template>(`/api/templates/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteTemplate: (id: string) => request<void>(`/api/templates/${id}`, { method: "DELETE" }),
  duplicateTemplate: (id: string) =>
    request<Template>(`/api/templates/${id}/duplicate`, { method: "POST" }),

  documents: (q = "", status = "") =>
    request<DocumentItem[]>(`/api/documents?q=${encodeURIComponent(q)}&status=${encodeURIComponent(status)}`),
  document: (id: string) => request<DocumentDetail>(`/api/documents/${id}`),
  createDocument: (body: { name?: string; template_id: string; profile_id?: string }) =>
    request<DocumentDetail>("/api/documents", { method: "POST", body: JSON.stringify(body) }),
  updateDocument: (id: string, body: Record<string, unknown>) =>
    request<DocumentDetail>(`/api/documents/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteDocument: (id: string) => request<void>(`/api/documents/${id}`, { method: "DELETE" }),
  bulkDeleteDocuments: (ids: string[]) =>
    request<void>("/api/documents/bulk-delete", { method: "POST", body: JSON.stringify({ ids }) }),
  duplicateDocument: (id: string) =>
    request<DocumentItem>(`/api/documents/${id}/duplicate`, { method: "POST" }),

  uploadImport: (file: File) => {
    const body = new FormData();
    body.set("file", file);
    return request<ImportSummary>("/api/imports", { method: "POST", body });
  },

  batches: () => request<Batch[]>("/api/batches"),
  batch: (id: string) => request<Batch>(`/api/batches/${id}`),
  createBatch: (body: {
    name: string;
    template_id: string;
    profile_id: string;
    import_id: string;
    export_format: string;
    naming: string;
    individual: boolean;
    combined: boolean;
  }) => request<Batch>("/api/batches", { method: "POST", body: JSON.stringify(body) }),
  pauseBatch: (id: string) => request<Batch>(`/api/batches/${id}/pause`, { method: "POST" }),
  resumeBatch: (id: string) => request<Batch>(`/api/batches/${id}/resume`, { method: "POST" }),
  cancelBatch: (id: string) => request<Batch>(`/api/batches/${id}/cancel`, { method: "POST" }),

  exports: () => request<ExportRecord[]>("/api/exports"),
  deleteExport: (id: string) => request<void>(`/api/exports/${id}`, { method: "DELETE" }),
};

export function downloadExport(id: string) {
  window.location.href = `${API_URL}/api/exports/${id}/download`;
}

export function previewUrl(documentId: string) {
  return `${API_URL}/api/documents/${documentId}/preview`;
}

export function glyphImageUrl(id: string, setName: GlyphSetName, key: string, stamp: number) {
  return `${API_URL}/api/profiles/${id}/glyphs/${setName}/${encodeURIComponent(key)}?v=${stamp}`;
}
