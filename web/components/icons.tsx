import type { ReactNode } from "react";

const paths: Record<string, ReactNode> = {
  dashboard: <><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /></>,
  documents: <><path d="M7 3h7l5 5v13H7z" /><path d="M14 3v5h5" /><path d="M10 13h6M10 17h4" /></>,
  templates: <><rect x="3" y="4" width="18" height="14" /><path d="M3 9h18" /></>,
  handwriting: <><path d="M4 18c2-6 4-9 6-9s2 3 4 3 3-2 6-6" /><path d="M4 21h16" /></>,
  batch: <><path d="M4 7h16M4 12h16M4 17h10" /><path d="M17 15l3 3-3 3" /></>,
  exports: <><path d="M12 4v10" /><path d="M8 10l4 4 4-4" /><path d="M5 19h14" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19" /></>,
  moon: <><path d="M20 14.5A8 8 0 1 1 9.5 4 6.5 6.5 0 0 0 20 14.5z" /></>,
  sidebar: <><rect x="3" y="4" width="18" height="16" /><path d="M9 4v16" /></>,
  back: <><path d="M15 5 8 12l7 7" /><path d="M9 12h11" /></>,
  trash: <><path d="M4 7h16" /><path d="M9 7V5h6v2" /><path d="M7 7l1 13h8l1-13" /><path d="M10 11v6M14 11v6" /></>,
};

export function Icon({ name, size = 18 }: { name: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      {paths[name] || paths.documents}
    </svg>
  );
}
