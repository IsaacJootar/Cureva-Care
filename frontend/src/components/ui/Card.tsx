"use client";

import type { CSSProperties, ReactNode } from "react";

// Cards are tinted, never flat white (cureva-docs/09 "Cards are tinted").
// Large content panels use the neutral card gradient; status tiles pass their
// own wash via `background`/`border`.

export function Card({
  children,
  style,
  padding = "18px 20px",
}: {
  children: ReactNode;
  style?: CSSProperties;
  padding?: string | number;
}) {
  return (
    <div
      style={{
        background: "var(--cv-card-bg)",
        border: "1px solid var(--cv-card-border)",
        boxShadow: "var(--cv-card-shadow)",
        borderRadius: "var(--cv-radius-card)",
        padding,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export function CardTitle({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: 14,
      }}
    >
      <h2 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: 0 }}>{children}</h2>
      {right}
    </div>
  );
}

export function MicroLabel({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        fontSize: 10.5,
        letterSpacing: "0.5px",
        textTransform: "uppercase",
        color: "var(--cv-text-muted)",
        fontWeight: 600,
      }}
    >
      {children}
    </div>
  );
}
