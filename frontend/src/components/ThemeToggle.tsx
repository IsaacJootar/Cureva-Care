"use client";

import { useLayoutEffect, useState } from "react";
import { apiPatch } from "@/lib/api";
import { effectiveTheme, storedChoice, toggleTheme, type EffectiveTheme } from "@/lib/theme";
import { MoonIcon, SunIcon } from "./icons";

// Sun/moon toggle for the top bar (cureva-docs/09 "How the toggle works").
// Persists to localStorage immediately (no-flash) AND to the user's profile
// (users.theme_preference) so the choice follows them across devices.
export function ThemeToggle() {
  const [theme, setTheme] = useState<EffectiveTheme>("light");

  // Re-apply after React clears <html> attrs on the dev Strict-Mode remount;
  // a no-op in production. Also syncs local state to the real DOM value.
  useLayoutEffect(() => {
    const choice = storedChoice();
    const eff = effectiveTheme(choice);
    document.documentElement.setAttribute("data-theme", eff);
    setTheme(eff);
  }, []);

  function onToggle() {
    const next = toggleTheme();
    setTheme(next);
    // Persist to profile; harmless if not signed in (ignored on 401).
    apiPatch("/users/me", { theme_preference: next }).catch(() => {});
  }

  return (
    <button
      onClick={onToggle}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
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
      {theme === "dark" ? <SunIcon size={17} /> : <MoonIcon size={17} />}
    </button>
  );
}
