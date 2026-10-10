"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { ChevronLeftIcon, ChevronRightIcon, MoreVerticalIcon } from "../icons";

// Data table wrapped in a card; header row is uppercase muted micro-labels with
// hairline borders, body rows hairline-bottom only, no zebra striping
// (cureva-docs/09 "Data table").

export function Table({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        background: "var(--cv-card-bg)",
        border: "1px solid var(--cv-card-border)",
        borderRadius: "var(--cv-radius-card)",
        boxShadow: "var(--cv-card-shadow)",
        overflow: "hidden",
      }}
    >
      <table style={{ width: "100%", borderCollapse: "collapse" }}>{children}</table>
    </div>
  );
}

export function Th({ children, style }: { children?: ReactNode; style?: CSSProperties }) {
  return (
    <th
      style={{
        textAlign: "left",
        fontSize: 10.5,
        textTransform: "uppercase",
        letterSpacing: "0.5px",
        color: "var(--cv-text-muted)",
        fontWeight: 600,
        padding: "11px 14px",
        borderTop: "1px solid var(--cv-hairline)",
        borderBottom: "1px solid var(--cv-hairline)",
        ...style,
      }}
    >
      {children}
    </th>
  );
}

export function Td({ children, style }: { children?: ReactNode; style?: CSSProperties }) {
  return (
    <td
      style={{
        fontSize: 12.5,
        color: "var(--cv-text-secondary)",
        padding: "11px 14px",
        borderBottom: "1px solid var(--cv-hairline)",
        ...style,
      }}
    >
      {children}
    </td>
  );
}

// Pagination — Prev/Next render as one of two GATED variants (real button vs a
// non-interactive lookalike), never a single button with a computed string
// `disabled` attribute (cureva-docs/09 "Pagination" + "Button states").
export function Pagination({
  page,
  pageCount,
  total,
  pageSize,
  onPage,
}: {
  page: number; // 1-indexed
  pageCount: number;
  total: number;
  pageSize: number;
  onPage: (p: number) => void;
}) {
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(total, page * pageSize);
  const canPrev = page > 1;
  const canNext = page < pageCount;

  const navStyle = (enabled: boolean): CSSProperties => ({
    width: 28,
    height: 28,
    borderRadius: 7,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    border: "1px solid var(--cv-card-border)",
    background: "var(--cv-button-secondary-bg)",
    color: enabled ? "var(--cv-text-secondary)" : "var(--cv-toggle-off)",
    cursor: enabled ? "pointer" : "default",
  });

  const pages = Array.from({ length: pageCount }, (_, i) => i + 1).slice(
    Math.max(0, page - 3),
    Math.max(0, page - 3) + 5,
  );

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 14 }}>
      <span style={{ fontSize: 11.5, color: "var(--cv-text-muted)" }} className="cv-num">
        Showing {from}–{to} of {total}
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {canPrev ? (
          <button style={navStyle(true)} onClick={() => onPage(page - 1)} aria-label="Previous page">
            <ChevronLeftIcon size={15} />
          </button>
        ) : (
          <span style={navStyle(false)} aria-hidden>
            <ChevronLeftIcon size={15} />
          </span>
        )}
        {pages.map((p) => (
          <button
            key={p}
            onClick={() => onPage(p)}
            className="cv-num"
            style={{
              width: 28,
              height: 28,
              borderRadius: 7,
              border: p === page ? "none" : "1px solid var(--cv-card-border)",
              background: p === page ? "var(--cv-accent-solid)" : "var(--cv-button-secondary-bg)",
              color: p === page ? "#fff" : "var(--cv-text-secondary)",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            {p}
          </button>
        ))}
        {canNext ? (
          <button style={navStyle(true)} onClick={() => onPage(page + 1)} aria-label="Next page">
            <ChevronRightIcon size={15} />
          </button>
        ) : (
          <span style={navStyle(false)} aria-hidden>
            <ChevronRightIcon size={15} />
          </span>
        )}
      </div>
    </div>
  );
}

export interface RowAction {
  icon: ReactNode;
  label: string; // aria-label — icons only, no visible text
  onClick: () => void;
  destructive?: boolean;
}

// Icon-only kebab menu (cureva-docs/09 "Row actions menu"). Opens a small
// HORIZONTAL icon-button row; a destructive action sits after a divider, red,
// and should open the confirm dialog (its onClick does that).
export function RowActionsMenu({ actions }: { actions: RowAction[] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const nonDestructive = actions.filter((a) => !a.destructive);
  const destructive = actions.filter((a) => a.destructive);

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-flex", justifyContent: "flex-end" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Row actions"
        aria-haspopup="menu"
        style={{
          width: 26,
          height: 26,
          borderRadius: 7,
          border: "none",
          background: open ? "var(--cv-accent-soft)" : "transparent",
          color: "var(--cv-text-secondary)",
          cursor: "pointer",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <MoreVerticalIcon size={16} />
      </button>
      {open && (
        <div
          role="menu"
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            right: 0,
            display: "flex",
            alignItems: "center",
            gap: 2,
            background: "var(--cv-button-secondary-bg)",
            border: "1px solid var(--cv-card-border)",
            borderRadius: 10,
            boxShadow: "var(--cv-menu-shadow)",
            padding: 6,
            zIndex: 400,
          }}
        >
          {nonDestructive.map((a) => (
            <IconBtn key={a.label} action={a} close={() => setOpen(false)} />
          ))}
          {destructive.length > 0 && nonDestructive.length > 0 && (
            <span style={{ width: 1, height: 20, background: "var(--cv-hairline)", margin: "0 2px" }} />
          )}
          {destructive.map((a) => (
            <IconBtn key={a.label} action={a} close={() => setOpen(false)} danger />
          ))}
        </div>
      )}
    </div>
  );
}

function IconBtn({ action, close, danger }: { action: RowAction; close: () => void; danger?: boolean }) {
  return (
    <button
      role="menuitem"
      aria-label={action.label}
      title={action.label}
      onClick={() => {
        close();
        action.onClick();
      }}
      style={{
        width: 32,
        height: 32,
        borderRadius: 7,
        border: "none",
        background: "transparent",
        color: danger ? "var(--cv-button-danger-bg)" : "#52514e",
        cursor: "pointer",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {action.icon}
    </button>
  );
}
