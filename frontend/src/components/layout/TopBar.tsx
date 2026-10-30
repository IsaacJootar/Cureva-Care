"use client";

import type { ReactNode } from "react";
import { BellIcon } from "../icons";
import { ThemeToggle } from "../ThemeToggle";

// Frosted-glass top bar (cureva-docs/09 "Top bar"): title + subtitle on the
// left; on the right, filter chips, then the theme toggle, then the
// notification bell, then the page's single primary action — in that order
// (theme toggle immediately left of the bell).
export function TopBar({
  title,
  subtitle,
  chips,
  action,
}: {
  title: string;
  subtitle?: string;
  chips?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <header
      className="cv-topbar"
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "var(--cv-topbar-bg)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        borderBottom: "1px solid var(--cv-hairline)",
        padding: "14px 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
      }}
    >
      <div style={{ minWidth: 0, flex: "1 1 auto" }}>
        <h1 style={{ fontSize: 21, color: "var(--cv-text-primary)", margin: 0, lineHeight: 1.1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {title}
        </h1>
        {subtitle && (
          <p style={{ fontSize: 12, color: "var(--cv-text-muted)", margin: "3px 0 0" }}>{subtitle}</p>
        )}
      </div>
      <div className="cv-topbar-actions" style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
        {chips}
        <ThemeToggle />
        <button
          aria-label="Notifications"
          style={{
            width: 34,
            height: 34,
            borderRadius: 8,
            border: "1px solid var(--cv-card-border)",
            background: "var(--cv-button-secondary-bg)",
            color: "var(--cv-text-secondary)",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <BellIcon size={17} />
        </button>
        {action}
      </div>
    </header>
  );
}
