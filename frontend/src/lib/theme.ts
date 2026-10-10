// Theme helpers. The source of truth is localStorage key 'cv-theme'
// ('light' | 'dark' | 'system'), resolved to an effective light/dark and
// written to <html data-theme>. Mirrors the no-flash script in layout.tsx and
// is kept in sync with users.theme_preference on the profile.

export type ThemeChoice = "light" | "dark" | "system";
export type EffectiveTheme = "light" | "dark";

const KEY = "cv-theme";

export function systemTheme(): EffectiveTheme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function storedChoice(): ThemeChoice {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "light" || v === "dark" || v === "system") return v;
  } catch {
    /* ignore */
  }
  return "system";
}

export function effectiveTheme(choice: ThemeChoice = storedChoice()): EffectiveTheme {
  return choice === "system" ? systemTheme() : choice;
}

export function applyTheme(choice: ThemeChoice) {
  const effective = effectiveTheme(choice);
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", effective);
  }
  try {
    localStorage.setItem(KEY, choice);
  } catch {
    /* ignore */
  }
}

// Toggle between the two visible states (light <-> dark). An explicit choice
// is always stored, so the OS preference stops driving it after first toggle.
export function toggleTheme(): EffectiveTheme {
  const next: EffectiveTheme = effectiveTheme() === "dark" ? "light" : "dark";
  applyTheme(next);
  return next;
}
