"use client";

import type { ReactNode } from "react";
import type { Status } from "./Feedback";

// Stat tile (cureva-docs/09 "Stat tile"): status wash bg+border, a 26px icon
// badge tinted to the status, an uppercase micro-label, a big tabular number
// with an optional lighter secondary fragment, and an 11.5px status line.

const WASH: Record<Status, { bg: string; border: string; icon: string; badge: string }> = {
  neutral: { bg: "var(--cv-neutral-bg)", border: "var(--cv-neutral-border)", icon: "var(--cv-neutral-icon)", badge: "var(--cv-neutral-pill-bg)" },
  success: { bg: "var(--cv-success-bg)", border: "var(--cv-success-border)", icon: "var(--cv-success-icon)", badge: "var(--cv-success-pill-bg)" },
  warning: { bg: "var(--cv-warning-bg)", border: "var(--cv-warning-border)", icon: "var(--cv-warning-icon)", badge: "var(--cv-warning-pill-bg)" },
  danger: { bg: "var(--cv-danger-bg)", border: "var(--cv-danger-border)", icon: "var(--cv-danger-icon)", badge: "var(--cv-danger-pill-bg)" },
};

export function StatTile({
  status = "neutral",
  icon,
  label,
  value,
  secondary,
  statusLine,
  statusIcon,
}: {
  status?: Status;
  icon?: ReactNode;
  label: string;
  value: ReactNode;
  secondary?: ReactNode;
  statusLine?: ReactNode;
  statusIcon?: ReactNode;
}) {
  const w = WASH[status];
  return (
    <div
      style={{
        padding: "14px 16px",
        borderRadius: "var(--cv-radius-card)",
        background: w.bg,
        border: `1px solid ${w.border}`,
      }}
    >
      {icon && (
        <div
          style={{
            width: 26,
            height: 26,
            borderRadius: 8,
            background: w.badge,
            color: w.icon,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 10,
          }}
        >
          {icon}
        </div>
      )}
      <div
        style={{
          fontSize: 11,
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          color: "var(--cv-text-muted)",
          fontWeight: 600,
        }}
      >
        {label}
      </div>
      <div className="cv-num" style={{ fontSize: 26, fontWeight: 700, color: "var(--cv-text-primary)", marginTop: 3, lineHeight: 1.1 }}>
        {value}
        {secondary != null && (
          <span style={{ fontSize: 16, color: "var(--cv-text-muted)", fontWeight: 600 }}> {secondary}</span>
        )}
      </div>
      {statusLine && (
        <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11.5, color: w.icon, marginTop: 7 }}>
          {statusIcon}
          <span>{statusLine}</span>
        </div>
      )}
    </div>
  );
}
