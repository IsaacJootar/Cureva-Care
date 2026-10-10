"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { CheckIcon, ChevronDownIcon } from "../icons";

// Filter / date-range chip with its open-menu behaviour (cureva-docs/09
// "Filter chip" + "Filter & date-range chip menu"). Single-select closes on
// pick; multi-select stays open across picks and summarises the count.

export interface ChipOption {
  value: string;
  label: string;
}

function ChipShell({ label, children }: { label: ReactNode; children?: (close: () => void) => ReactNode }) {
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

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-flex" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          padding: "6px 12px",
          borderRadius: "var(--cv-radius-pill)",
          background: "linear-gradient(180deg,var(--cv-input-bg),var(--cv-button-secondary-bg))",
          border: "1px solid var(--cv-input-border)",
          fontSize: 12.5,
          color: "var(--cv-text-secondary)",
          cursor: "pointer",
        }}
      >
        {label}
        <ChevronDownIcon size={14} />
      </button>
      {open && children && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            left: 0,
            minWidth: 200,
            background: "var(--cv-button-secondary-bg)",
            border: "1px solid var(--cv-card-border)",
            borderRadius: 10,
            boxShadow: "var(--cv-menu-shadow)",
            padding: 6,
            zIndex: 400,
          }}
        >
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  );
}

const rowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  width: "100%",
  padding: "8px 9px",
  borderRadius: 7,
  border: "none",
  background: "transparent",
  color: "var(--cv-text-primary)",
  fontSize: 12.5,
  cursor: "pointer",
  textAlign: "left",
};

export function SingleSelectChip({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: ChipOption[];
  value: string;
  onChange: (v: string) => void;
}) {
  const current = options.find((o) => o.value === value);
  return (
    <ChipShell label={current ? `${label}: ${current.label}` : label}>
      {(close) => (
        <>
          {options.map((o) => (
            <button
              key={o.value}
              style={rowStyle}
              onClick={() => {
                onChange(o.value);
                close();
              }}
            >
              <span style={{ width: 15, color: "var(--cv-accent-solid)" }}>
                {o.value === value ? <CheckIcon size={14} /> : null}
              </span>
              {o.label}
            </button>
          ))}
        </>
      )}
    </ChipShell>
  );
}

export function MultiSelectChip({
  label,
  options,
  values,
  onChange,
}: {
  label: string;
  options: ChipOption[];
  values: string[];
  onChange: (v: string[]) => void;
}) {
  const summary =
    values.length === 0 ? `${label}: All` : values.length === 1 ? `${label}: ${options.find((o) => o.value === values[0])?.label}` : `${label}: ${values.length} selected`;
  const toggle = (v: string) =>
    onChange(values.includes(v) ? values.filter((x) => x !== v) : [...values, v]);

  return (
    <ChipShell label={summary}>
      {() => (
        <>
          {options.map((o) => {
            const checked = values.includes(o.value);
            return (
              <button key={o.value} style={rowStyle} onClick={() => toggle(o.value)}>
                <span
                  style={{
                    width: 15,
                    height: 15,
                    borderRadius: 4,
                    border: `1.5px solid ${checked ? "var(--cv-accent-solid)" : "var(--cv-input-border)"}`,
                    background: checked ? "var(--cv-accent-solid)" : "transparent",
                    color: "#fff",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  {checked && <CheckIcon size={11} />}
                </span>
                {o.label}
              </button>
            );
          })}
        </>
      )}
    </ChipShell>
  );
}
