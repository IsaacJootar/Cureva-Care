"use client";

import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { AlertTriangleIcon } from "../icons";

// Labelled input with error-after-submit behaviour (cureva-docs/09 "Form
// field, validation & submission"). The error is shown by the parent form only
// after a submit attempt; from then on it clears live as the value becomes
// valid. A read-only field uses the page background so it visibly can't focus.

const labelStyle: React.CSSProperties = {
  fontSize: 11.5,
  fontWeight: 600,
  color: "var(--cv-text-secondary)",
  display: "block",
  marginBottom: 5,
};

function controlStyle(error?: boolean, readOnly?: boolean): React.CSSProperties {
  return {
    width: "100%",
    fontSize: 12.5,
    color: "var(--cv-text-primary)",
    background: readOnly ? "var(--cv-bg)" : "var(--cv-input-bg)",
    border: `${error ? 1.5 : 1}px solid ${error ? "var(--cv-danger-text)" : "var(--cv-input-border)"}`,
    borderRadius: "var(--cv-radius-control)",
    padding: "9px 11px",
    outline: "none",
  };
}

export function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 5,
        color: "var(--cv-danger-text)",
        fontSize: 11,
        marginTop: 5,
      }}
    >
      <AlertTriangleIcon size={13} />
      {message}
    </div>
  );
}

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: ReactNode;
  error?: string;
}

export function TextField({ label, error, id, readOnly, ...rest }: TextFieldProps) {
  return (
    <div>
      {label && (
        <label htmlFor={id} style={labelStyle}>
          {label}
        </label>
      )}
      <input id={id} readOnly={readOnly} style={controlStyle(!!error, readOnly)} {...rest} />
      <FieldError message={error} />
    </div>
  );
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: ReactNode;
  error?: string;
  children: ReactNode;
}

export function SelectField({ label, error, id, children, ...rest }: SelectFieldProps) {
  return (
    <div>
      {label && (
        <label htmlFor={id} style={labelStyle}>
          {label}
        </label>
      )}
      <select id={id} style={controlStyle(!!error)} {...rest}>
        {children}
      </select>
      <FieldError message={error} />
    </div>
  );
}
