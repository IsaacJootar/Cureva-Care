"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import { CheckIcon } from "../icons";

// Primary/submit, secondary/ghost, and destructive buttons
// (cureva-docs/09 "Buttons" + "Button states").
//
// Disabled gotcha: a real HTML `disabled` attribute disables on PRESENCE, so a
// string value like disabled="false" still disables. We therefore gate on a
// controlled boolean prop (React handles the boolean attribute correctly) and
// on conditional rendering of the loading/success variants — never a
// string-valued attribute.
//
// `--cv-button-primary-bg` (#111110 light / #f2f1ec dark) is reserved for the
// ONE submit/commit action on a screen or card — not tabs, chips, toggles,
// pagination, or row-action icons.

type Variant = "primary" | "secondary" | "danger";

interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "disabled"> {
  variant?: Variant;
  disabled?: boolean;
  loading?: boolean;
  loadingLabel?: string;
  success?: boolean;
  successLabel?: string;
  leftIcon?: ReactNode;
  fullWidth?: boolean;
  children: ReactNode;
}

function variantStyle(variant: Variant): React.CSSProperties {
  switch (variant) {
    case "secondary":
      return {
        background: "var(--cv-button-secondary-bg)",
        color: "var(--cv-text-secondary)",
        border: "1px solid var(--cv-button-secondary-border)",
      };
    case "danger":
      return {
        background: "var(--cv-button-danger-bg)",
        color: "var(--cv-button-danger-text)",
        border: "1px solid transparent",
      };
    default:
      return {
        background: "var(--cv-button-primary-bg)",
        color: "var(--cv-button-primary-text)",
        border: "1px solid transparent",
      };
  }
}

export function Button({
  variant = "primary",
  disabled = false,
  loading = false,
  loadingLabel,
  success = false,
  successLabel = "Saved",
  leftIcon,
  fullWidth = false,
  children,
  style,
  type = "button",
  ...rest
}: ButtonProps) {
  const base: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    padding: "9px 16px",
    borderRadius: "var(--cv-radius-control)",
    fontSize: 12.5,
    fontWeight: 600,
    cursor: "pointer",
    width: fullWidth ? "100%" : undefined,
    transition: "background 140ms, opacity 140ms",
    lineHeight: 1,
    ...style,
  };

  // Success flash — overrides the variant fill briefly (caller-controlled).
  if (success) {
    return (
      <button
        type={type}
        disabled
        style={{
          ...base,
          background: "var(--cv-button-success-bg)",
          color: "#ffffff",
          border: "1px solid transparent",
          cursor: "default",
        }}
        {...rest}
      >
        <CheckIcon size={15} />
        {successLabel}
      </button>
    );
  }

  // Loading — reduced-opacity primary fill (reserved for THIS state only, never
  // for disabled), spinner, present-participle label, cannot double-submit.
  if (loading) {
    return (
      <button
        type={type}
        disabled
        aria-busy="true"
        style={{ ...base, ...variantStyle(variant), opacity: 0.75, cursor: "default" }}
        {...rest}
      >
        <span
          className="cv-spin"
          style={{
            width: 14,
            height: 14,
            borderRadius: "50%",
            border: "2px solid rgba(255,255,255,0.5)",
            borderTopColor: "#fff",
            display: "inline-block",
          }}
        />
        {loadingLabel ?? children}
      </button>
    );
  }

  // Disabled — flat grey, NOT reduced-opacity primary (kept visually distinct
  // from loading). Real boolean attribute, safe in React.
  if (disabled) {
    return (
      <button
        type={type}
        disabled
        style={{
          ...base,
          background: "var(--cv-button-disabled-bg)",
          color: "var(--cv-button-disabled-text)",
          border: "1px solid transparent",
          cursor: "not-allowed",
        }}
        {...rest}
      >
        {leftIcon}
        {children}
      </button>
    );
  }

  return (
    <button type={type} style={{ ...base, ...variantStyle(variant) }} {...rest}>
      {leftIcon}
      {children}
    </button>
  );
}
