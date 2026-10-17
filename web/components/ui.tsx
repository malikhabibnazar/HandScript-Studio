"use client";

import Link from "next/link";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { toneFor } from "@/lib/format";
import { Icon } from "./icons";

type Toast = { id: number; text: string; tone: string };
const ToastContext = createContext<(text: string, tone?: string) => void>(() => undefined);

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone = "info") => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, text, tone }]);
    setTimeout(() => setToasts((current) => current.filter((item) => item.id !== id)), 3200);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toasts">
        {toasts.map((toast) => <div key={toast.id} className={`toast ${toast.tone}`}>{toast.text}</div>)}
      </div>
    </ToastContext.Provider>
  );
}

export function Badge({ value }: { value: string }) {
  return <span className={`badge ${toneFor(value)}`}>{value}</span>;
}

export function BackLink({ href }: { href: string }) {
  return (
    <Link href={href} className="back-link">
      <Icon name="back" size={16} />
      Back
    </Link>
  );
}

export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      <div className="row">{children}</div>
    </header>
  );
}

export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
        <h2>{title}</h2>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

export function Empty({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{body}</p>
      {action ? <div className="row" style={{ justifyContent: "center", marginTop: 14 }}>{action}</div> : null}
    </div>
  );
}
