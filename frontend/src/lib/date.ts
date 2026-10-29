// Human-readable dates for the UI. Backend dates arrive as "YYYY-MM-DD" (or an
// ISO datetime); render them as "2nd February 2024" so nothing reads like a raw
// machine date. Falls back to the raw value if it can't be parsed, and to "—"
// when empty.
function ordinal(n: number): string {
  const v = n % 100;
  if (v >= 11 && v <= 13) return "th";
  return ({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[n % 10] ?? "th";
}

export function prettyDate(value?: string | null): string {
  if (!value) return "—";
  // Treat a plain date as local midnight so it doesn't shift across time zones.
  const d = new Date(value.length <= 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(d.getTime())) return value;
  const day = d.getDate();
  const month = d.toLocaleString("en-GB", { month: "long" });
  return `${day}${ordinal(day)} ${month} ${d.getFullYear()}`;
}

// Compact variant: "2 Feb 2024" — for tight spots like table cells.
export function prettyDateShort(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value.length <= 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}
