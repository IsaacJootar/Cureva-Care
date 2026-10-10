"use client";

// One toggle, two uses: the theme toggle and any admin on/off flag
// (cureva-docs/09 "Toggle switch"). 38x22 track, accent-blue on / neutral off,
// 18px knob. A label and optional state caption sit to the right.

export function Toggle({
  checked,
  onChange,
  label,
  caption,
  ariaLabel,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label?: string;
  caption?: string;
  ariaLabel?: string;
}) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={ariaLabel ?? label}
        onClick={() => onChange(!checked)}
        style={{
          width: 38,
          height: 22,
          borderRadius: 20,
          border: "none",
          cursor: "pointer",
          background: checked ? "var(--cv-accent-solid)" : "var(--cv-toggle-off)",
          position: "relative",
          transition: "background 150ms",
          flexShrink: 0,
          padding: 0,
        }}
      >
        <span
          style={{
            position: "absolute",
            top: 2,
            left: checked ? 18 : 2,
            width: 18,
            height: 18,
            borderRadius: "50%",
            background: "#fff",
            boxShadow: "0 1px 3px rgba(11,11,11,0.25)",
            transition: "left 18ms ease, transform 150ms ease",
          }}
        />
      </button>
      {(label || caption) && (
        <span style={{ display: "flex", flexDirection: "column", lineHeight: 1.25 }}>
          {label && <span style={{ fontSize: 12.5, color: "var(--cv-text-primary)" }}>{label}</span>}
          {caption && <span style={{ fontSize: 11, color: "var(--cv-text-muted)" }}>{caption}</span>}
        </span>
      )}
    </div>
  );
}
