"use client";

import Link from "next/link";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
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

export type ConfirmOptions = {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  action?: () => Promise<void>;
};

function pendingLabel(label: string) {
  if (label.startsWith("Delete")) return "Deleting…";
  if (label.startsWith("Remove")) return "Removing…";
  if (label.startsWith("Clear")) return "Clearing…";
  return "Working…";
}

export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  cancelLabel,
  destructive,
  pending,
  error,
  onConfirm,
  onCancel,
}: {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  destructive: boolean;
  pending: boolean;
  error: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const pendingRef = useRef(pending);
  const onCancelRef = useRef(onCancel);
  pendingRef.current = pending;
  onCancelRef.current = onCancel;

  useEffect(() => {
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    cancelRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        if (pendingRef.current) return;
        event.preventDefault();
        onCancelRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = [...dialogRef.current.querySelectorAll<HTMLElement>("button:not(:disabled)")];
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
      if (previouslyFocused?.isConnected) previouslyFocused.focus();
    };
  }, []);

  return (
    <div className="modal-back confirm-back" onClick={() => { if (!pending) onCancel(); }}>
      <div
        className="modal confirm-dialog"
        ref={dialogRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-message"
        aria-busy={pending}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="confirm-title">{title}</h2>
        <div className="modal-body">
          <p id="confirm-message" className="secondary">{message}</p>
          {error ? <p className="confirm-error" role="alert">{error}</p> : null}
        </div>
        <div className="row confirm-actions">
          <button ref={cancelRef} type="button" className="btn secondary" disabled={pending} onClick={onCancel}>{cancelLabel}</button>
          <button type="button" className={destructive ? "btn danger solid" : "btn primary"} disabled={pending} onClick={onConfirm}>
            {pending ? pendingLabel(confirmLabel) : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

type ConfirmRequest = Required<Pick<ConfirmOptions, "title" | "message" | "confirmLabel" | "cancelLabel" | "destructive">> & {
  action?: () => Promise<void>;
  resolve: (value: boolean) => void;
};

export function useConfirm() {
  const [request, setRequest] = useState<ConfirmRequest | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const requestRef = useRef<ConfirmRequest | null>(null);
  const pendingRef = useRef(false);

  const confirm = useCallback((options: ConfirmOptions) => {
    requestRef.current?.resolve(false);
    return new Promise<boolean>((resolve) => {
      const next: ConfirmRequest = {
        title: options.title,
        message: options.message,
        confirmLabel: options.confirmLabel ?? "Delete",
        cancelLabel: options.cancelLabel ?? "Cancel",
        destructive: options.destructive ?? true,
        action: options.action,
        resolve,
      };
      requestRef.current = next;
      pendingRef.current = false;
      setPending(false);
      setError("");
      setRequest(next);
    });
  }, []);

  const cancel = useCallback(() => {
    if (pendingRef.current) return;
    requestRef.current?.resolve(false);
    requestRef.current = null;
    setRequest(null);
    setError("");
  }, []);

  const accept = useCallback(async () => {
    const current = requestRef.current;
    if (!current || pendingRef.current) return;
    if (!current.action) {
      current.resolve(true);
      requestRef.current = null;
      setRequest(null);
      return;
    }
    pendingRef.current = true;
    setPending(true);
    setError("");
    try {
      await current.action();
      if (requestRef.current !== current) return;
      current.resolve(true);
      requestRef.current = null;
      pendingRef.current = false;
      setPending(false);
      setRequest(null);
    } catch (err) {
      if (requestRef.current !== current) return;
      pendingRef.current = false;
      setPending(false);
      setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
    }
  }, []);

  useEffect(() => () => {
    requestRef.current?.resolve(false);
    requestRef.current = null;
  }, []);

  const dialog = request ? (
    <ConfirmDialog
      title={request.title}
      message={request.message}
      confirmLabel={request.confirmLabel}
      cancelLabel={request.cancelLabel}
      destructive={request.destructive}
      pending={pending}
      error={error}
      onConfirm={() => { void accept(); }}
      onCancel={cancel}
    />
  ) : null;

  return { confirm, dialog };
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
