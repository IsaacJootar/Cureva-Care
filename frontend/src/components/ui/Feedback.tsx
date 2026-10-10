"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { CheckIcon, InfoIcon } from "../icons";

export type Status = "success" | "warning" | "danger" | "neutral";

const PILL: Record<Status, { bg: string; text: string }> = {
  success: { bg: "var(--cv-success-pill-bg)", text: "var(--cv-success-pill-text)" },
  warning: { bg: "var(--cv-warning-pill-bg)", text: "var(--cv-warning-pill-text)" },
  danger: { bg: "var(--cv-danger-pill-bg)", text: "var(--cv-danger-pill-text)" },
  neutral: { bg: "var(--cv-neutral-pill-bg)", text: "var(--cv-neutral-pill-text)" },
};

export function StatusPill({
  status,
  children,
  icon,
}: {
  status: Status;
  children: ReactNode;
  icon?: ReactNode;
}) {
  const tk = PILL[status];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "3px 9px",
        borderRadius: "var(--cv-radius-pill)",
        background: tk.bg,
        color: tk.text,
        fontSize: 11,
        fontWeight: 600,
      }}
    >
      {icon}
      {children}
    </span>
  );
}

// Skeletons — first paint only. A background refresh must NOT re-trigger them
// (cureva-docs/09 "Loading / skeleton").
export function Skeleton({ width, height = 12, style }: { width?: number | string; height?: number; style?: CSSProperties }) {
  return <span className="cv-skel" style={{ display: "block", width: width ?? "100%", height, ...style }} />;
}

export function StatTileSkeleton() {
  return (
    <div
      style={{
        padding: "14px 16px",
        borderRadius: "var(--cv-radius-card)",
        background: "var(--cv-card-bg)",
        border: "1px solid var(--cv-card-border)",
      }}
    >
      <Skeleton width={26} height={26} style={{ borderRadius: 8, marginBottom: 12 }} />
      <Skeleton width="55%" height={9} style={{ marginBottom: 10 }} />
      <Skeleton width="40%" height={22} />
    </div>
  );
}

export function EmptyState({
  icon,
  heading,
  hint,
  action,
}: {
  icon?: ReactNode;
  heading: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div
      style={{
        border: "1px dashed var(--cv-empty-border)",
        borderRadius: "var(--cv-radius-card)",
        padding: "34px 24px",
        textAlign: "center",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 6,
      }}
    >
      {icon && <span style={{ color: "var(--cv-text-muted)" }}>{icon}</span>}
      <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>{heading}</div>
      {hint && <div style={{ fontSize: 11, color: "var(--cv-text-muted)", maxWidth: 320 }}>{hint}</div>}
      {action && <div style={{ marginTop: 10 }}>{action}</div>}
    </div>
  );
}

// Click-to-open info tooltip (works on touch, unlike hover).
export function Tooltip({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  return (
    <span ref={ref} style={{ position: "relative", display: "inline-flex" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="More information"
        style={{
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: "var(--cv-input-border)",
          border: "none",
          color: "var(--cv-text-secondary)",
          fontSize: 9,
          cursor: "pointer",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 0,
        }}
      >
        <InfoIcon size={10} />
      </button>
      {open && (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            right: 0,
            width: 240,
            background: "#111110",
            color: "#e7e6e1",
            fontSize: 11.5,
            lineHeight: 1.5,
            borderRadius: 8,
            padding: "9px 11px",
            zIndex: 500,
            boxShadow: "var(--cv-menu-shadow)",
          }}
        >
          {text}
        </span>
      )}
    </span>
  );
}

// Determinate upload progress (the browser knows real progress) — never an
// indeterminate spinner (cureva-docs/09 "Upload / processing progress bar").
export function UploadProgress({ percent, label = "Uploading register photo…" }: { percent: number; label?: string }) {
  const done = percent >= 100;
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, marginBottom: 6 }}>
        <span style={{ color: done ? "var(--cv-success-text)" : "var(--cv-text-secondary)", display: "inline-flex", gap: 5, alignItems: "center" }}>
          {done && <CheckIcon size={14} />}
          {done ? "Uploaded — ready to extract" : label}
        </span>
        {!done && <span className="cv-num" style={{ color: "var(--cv-text-muted)" }}>{Math.round(percent)}%</span>}
      </div>
      {!done && (
        <div style={{ height: 6, borderRadius: 4, background: "var(--cv-button-disabled-bg)", overflow: "hidden" }}>
          <div
            style={{
              height: "100%",
              width: `${Math.min(100, Math.max(0, percent))}%`,
              background: "var(--cv-accent-solid)",
              borderRadius: 4,
              transition: "width 140ms",
            }}
          />
        </div>
      )}
    </div>
  );
}
