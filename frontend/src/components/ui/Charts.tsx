"use client";

import type { ReactNode } from "react";
import { Tooltip } from "./Feedback";

interface Ratio {
  numerator: number;
  denominator: number;
  rate: number | null;
}

// A metric with its rate AND its denominator + completeness — never a bare
// percentage (rule #5). A thin meter visualises the rate.
export function MetricMeter({ label, ratio, tooltip }: { label: string; ratio: Ratio; tooltip?: string }) {
  const pct = ratio.rate != null ? Math.round(ratio.rate * 100) : null;
  return (
    <div style={{ padding: "12px 0", borderBottom: "1px solid var(--cv-hairline)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
        <span style={{ fontSize: 12.5, color: "var(--cv-text-secondary)", display: "inline-flex", alignItems: "center", gap: 5 }}>
          {label}
          {tooltip && <Tooltip text={tooltip} />}
        </span>
        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--cv-text-primary)" }} className="cv-num">
          {pct != null ? `${pct}%` : "—"}
          <span style={{ fontSize: 11, color: "var(--cv-text-muted)", fontWeight: 400 }}>
            {" "}
            ({ratio.numerator}/{ratio.denominator})
          </span>
        </span>
      </div>
      <div style={{ height: 6, borderRadius: 4, background: "var(--cv-button-disabled-bg)", overflow: "hidden" }}>
        <div
          style={{
            height: "100%",
            width: `${pct ?? 0}%`,
            background: "var(--cv-accent-gradient)",
            borderRadius: 4,
            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.35)",
          }}
        />
      </div>
    </div>
  );
}

// Horizontal care-journey funnel — stages darken left-to-right to show
// progression (cureva-docs/09 "Chart card").
export function Funnel({ stages }: { stages: { label: string; value: number }[] }) {
  const max = Math.max(1, ...stages.map((s) => s.value));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {stages.map((s, i) => {
        const pct = Math.round((s.value / max) * 100);
        const darken = 1 - i * 0.14;
        return (
          <div key={s.label}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, marginBottom: 4 }}>
              <span style={{ color: "var(--cv-text-secondary)" }}>{s.label}</span>
              <span className="cv-num" style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{s.value}</span>
            </div>
            <div style={{ height: 22, borderRadius: 6, background: "var(--cv-button-disabled-bg)", overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  width: `${Math.max(pct, 3)}%`,
                  background: `linear-gradient(90deg, rgba(47,95,214,${0.95 * darken}), rgba(47,95,214,${0.6 * darken}))`,
                  borderRadius: 6,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Simple vertical bar group (counts).
export function BarGroup({ data }: { data: { label: string; value: number; status?: string }[] }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  const color = (s?: string) =>
    s === "danger" ? "var(--cv-danger-icon)" : s === "warning" ? "var(--cv-warning-icon)" : "var(--cv-accent-solid)";
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 14, height: 160, paddingTop: 10 }}>
      {data.map((d) => (
        <div key={d.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
          <span className="cv-num" style={{ fontSize: 11.5, color: "var(--cv-text-primary)", fontWeight: 600 }}>{d.value}</span>
          <div
            style={{
              width: "70%",
              height: `${Math.max((d.value / max) * 120, 3)}px`,
              background: color(d.status),
              borderRadius: "4px 4px 0 0",
              boxShadow: "inset 0 1px 0 rgba(255,255,255,0.35)",
            }}
          />
          <span style={{ fontSize: 10.5, color: "var(--cv-text-muted)", textAlign: "center" }}>{d.label}</span>
        </div>
      ))}
    </div>
  );
}

export function ChartPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div
      style={{
        background: "var(--cv-card-bg)",
        border: "1px solid var(--cv-card-border)",
        boxShadow: "var(--cv-card-shadow)",
        borderRadius: "var(--cv-radius-card)",
        padding: "18px 20px",
      }}
    >
      <h2 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: "0 0 14px" }}>{title}</h2>
      {children}
    </div>
  );
}
