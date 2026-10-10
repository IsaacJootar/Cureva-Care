"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import { AlertTriangleIcon, CheckIcon, InfoIcon, XIcon } from "../icons";

// Top-right, fixed to the viewport, stacking downward, newest on top. Colours
// come from the matching status wash; a 2px underline drains over the toast's
// lifetime as a visible countdown. Auto-dismiss ~4.5s or × to close early
// (cureva-docs/09 "Toast notification").

type ToastType = "success" | "warning" | "danger" | "info";

interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastApi {
  toast: (type: ToastType, message: string) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);
const LIFETIME_MS = 4500;

const TOKENS: Record<ToastType, { bg: string; border: string; text: string; icon: ReactNode }> = {
  success: {
    bg: "var(--cv-success-bg)",
    border: "var(--cv-success-border)",
    text: "var(--cv-success-text)",
    icon: <CheckIcon size={15} />,
  },
  warning: {
    bg: "var(--cv-warning-bg)",
    border: "var(--cv-warning-border)",
    text: "var(--cv-warning-text)",
    icon: <AlertTriangleIcon size={15} />,
  },
  danger: {
    bg: "var(--cv-danger-bg)",
    border: "var(--cv-danger-border)",
    text: "var(--cv-danger-text)",
    icon: <AlertTriangleIcon size={15} />,
  },
  info: {
    bg: "var(--cv-neutral-bg)",
    border: "var(--cv-neutral-border)",
    text: "var(--cv-neutral-text)",
    icon: <InfoIcon size={15} />,
  },
};

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const remove = useCallback((id: number) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (type: ToastType, message: string) => {
      const id = nextId++;
      setItems((prev) => [{ id, type, message }, ...prev]); // newest on top
      setTimeout(() => remove(id), LIFETIME_MS);
    },
    [remove],
  );

  const api: ToastApi = {
    toast,
    success: (m) => toast("success", m),
    error: (m) => toast("danger", m),
    warning: (m) => toast("warning", m),
    info: (m) => toast("info", m),
  };

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        style={{
          position: "fixed",
          top: 16,
          right: 16,
          zIndex: 1000,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          maxWidth: 340,
        }}
      >
        {items.map((t) => {
          const tk = TOKENS[t.type];
          return (
            <div
              key={t.id}
              role="status"
              style={{
                background: tk.bg,
                border: `1px solid ${tk.border}`,
                borderRadius: 10,
                boxShadow: "var(--cv-menu-shadow)",
                padding: "11px 12px 13px",
                position: "relative",
                overflow: "hidden",
                display: "flex",
                alignItems: "flex-start",
                gap: 9,
              }}
            >
              <span style={{ color: tk.text, flexShrink: 0, marginTop: 1 }}>{tk.icon}</span>
              <span style={{ color: "var(--cv-text-primary)", fontSize: 12.5, flex: 1 }}>
                {t.message}
              </span>
              <button
                onClick={() => remove(t.id)}
                aria-label="Dismiss"
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--cv-text-muted)",
                  padding: 0,
                  lineHeight: 0,
                }}
              >
                <XIcon size={14} />
              </button>
              <span
                style={{
                  position: "absolute",
                  left: 0,
                  bottom: 0,
                  height: 2,
                  background: tk.text,
                  width: "100%",
                  transformOrigin: "left",
                  animation: `cv-toast-drain ${LIFETIME_MS}ms linear forwards`,
                }}
              />
            </div>
          );
        })}
      </div>
      <style>{`@keyframes cv-toast-drain{from{transform:scaleX(1)}to{transform:scaleX(0)}}`}</style>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
