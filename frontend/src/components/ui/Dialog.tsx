"use client";

import { useEffect, type ReactNode } from "react";
import { AlertTriangleIcon } from "../icons";
import { Button } from "./Button";

// Base modal: full-screen scrim (click to cancel), centered panel, Esc closes.
export function Modal({
  open,
  onClose,
  children,
  width = 440,
}: {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  width?: number;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
      style={{
        position: "fixed",
        inset: 0,
        background: "var(--cv-scrim)",
        display: "grid",
        placeItems: "center",
        zIndex: 900,
        padding: 16,
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        style={{
          width,
          maxWidth: "100%",
          // Never taller than the viewport (minus the scrim's 16px gutter each
          // side); scroll inside when the content doesn't fit, so nothing below
          // the fold is unreachable.
          maxHeight: "calc(100vh - 32px)",
          overflowY: "auto",
          background: "var(--cv-card-bg)",
          border: "1px solid var(--cv-card-border)",
          borderRadius: 12,
          boxShadow: "var(--cv-menu-shadow)",
          padding: 22,
        }}
      >
        {children}
      </div>
    </div>
  );
}

// Destructive-action confirm dialog (cureva-docs/09). Names the concrete,
// irreversible consequence — never a generic "Are you sure?". Destructive
// button is always on the right, always red, never the default focus.
export function ConfirmDialog({
  open,
  title,
  consequence,
  confirmLabel = "Delete",
  onCancel,
  onConfirm,
  loading = false,
}: {
  open: boolean;
  title: string;
  consequence: string;
  confirmLabel?: string;
  onCancel: () => void;
  onConfirm: () => void;
  loading?: boolean;
}) {
  return (
    <Modal open={open} onClose={onCancel} width={380}>
      <div
        style={{
          width: 38,
          height: 38,
          borderRadius: 9,
          background: "var(--cv-danger-bg)",
          border: "1px solid var(--cv-danger-border)",
          color: "var(--cv-danger-icon)",
          display: "grid",
          placeItems: "center",
          marginBottom: 14,
        }}
      >
        <AlertTriangleIcon size={18} />
      </div>
      <h2 style={{ fontSize: 15, color: "var(--cv-text-primary)", margin: "0 0 7px" }}>{title}</h2>
      <p style={{ fontSize: 12.5, color: "var(--cv-text-secondary)", margin: "0 0 18px", lineHeight: 1.5 }}>
        {consequence}
      </p>
      <div style={{ display: "flex", gap: 10 }}>
        <Button variant="secondary" fullWidth onClick={onCancel}>
          Cancel
        </Button>
        <Button variant="danger" fullWidth onClick={onConfirm} loading={loading} loadingLabel="Working…">
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
