"use client";

import { useEffect, useState } from "react";
import { listSettings, updateSetting, type PlatformSetting } from "@/lib/ops";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { Toggle } from "@/components/ui/Toggle";
import { useToast } from "@/components/ui/Toast";

// --- Plain-language presentation for every technical setting ---------------
// The backend stores raw keys and 0–1 thresholds; here we give each one a
// friendly name, a one-line explanation, and a human unit (percentage or days)
// so a non-technical admin can relate to it. "percent" settings are stored as
// a 0–1 decimal but shown and edited as a whole-number percentage.
type Unit = "percent" | "days" | "count";
interface Meta {
  cat: string;
  label: string;
  blurb: string;
  unit: Unit;
  unitLabel?: string; // overrides the suffix for "count"
}

const CATEGORIES: { id: string; title: string; caption: string }[] = [
  {
    id: "alerts",
    title: "Alerts & early warnings",
    caption: "When Cureva should flag a facility as needing attention.",
  },
  {
    id: "matching",
    title: "Matching records to the right mother",
    caption: "How carefully the system links repeat visits to the same woman.",
  },
  {
    id: "ai",
    title: "Reading scanned registers (AI)",
    caption: "How sure the AI must be before a value is accepted without a human check.",
  },
];

const META: Record<string, Meta> = {
  stale_facility_alert_days: {
    cat: "alerts",
    label: "Quiet-facility alert",
    unit: "days",
    blurb: "Warn us when a facility hasn’t submitted any new records for this long.",
  },
  referral_backlog_days: {
    cat: "alerts",
    label: "Referral waiting too long",
    unit: "days",
    blurb: "Flag a referral that has stayed open longer than this.",
  },
  coverage_alert_floor: {
    cat: "alerts",
    label: "Low coverage",
    unit: "percent",
    blurb: "Warn when the share of mothers screened or treated at a facility falls below this.",
  },
  severe_cluster_rate: {
    cat: "alerts",
    label: "Severe-outcome spike",
    unit: "percent",
    blurb: "Warn when deaths and stillbirths reach this share of births at a facility.",
  },
  high_risk_contact_gap_days: {
    cat: "alerts",
    label: "High-risk mother overdue",
    unit: "days",
    blurb: "Flag a high-risk pregnancy with no recorded check-up for this many days.",
  },
  identity_candidate_confidence_threshold: {
    cat: "matching",
    label: "Suggest a match when this sure",
    unit: "percent",
    blurb: "How confident the system must be before it suggests two records belong to the same mother.",
  },
  identity_strict_name_floor: {
    cat: "matching",
    label: "Names must match at least",
    unit: "percent",
    blurb: "How closely names must match — alongside the same card number — to link records automatically.",
  },
  identity_card_reuse_window_days: {
    cat: "matching",
    label: "Trust a card number for",
    unit: "days",
    blurb: "A matching card number older than this is treated as unreliable (clinics reuse numbers) and sent for manual review.",
  },
  new_episode_gap_days: {
    cat: "matching",
    label: "Treat as a new pregnancy after",
    unit: "days",
    blurb: "If a new check-up arrives this long after the last one, count it as a new pregnancy rather than the same one.",
  },
  register_mismatch_min_signal: {
    cat: "matching",
    label: "Wrong-register warning",
    unit: "count",
    unitLabel: "matching details",
    blurb: "How many matching details it takes before the system suspects an entry was written in the wrong register book.",
  },
  ai_extraction_confidence_threshold: {
    cat: "ai",
    label: "Ask a person to confirm below",
    unit: "percent",
    blurb: "When the AI is less sure than this about a value it read from a page, a person must confirm it before it’s saved.",
  },
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<PlatformSetting[] | null>(null);

  useEffect(() => {
    listSettings().then(setSettings).catch(() => setSettings([]));
  }, []);

  return (
    <AppShell
      title="Settings"
      subtitle="Tune how Cureva watches your data — in plain language. Changes apply right away."
      allowedRoles={["systems_admin"]}
    >
      {!settings ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 680, margin: "0 auto" }}>
          {Array.from({ length: 3 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 26, maxWidth: 680, margin: "0 auto" }}>
          {CATEGORIES.map((cat) => {
            const rows = settings.filter((s) => (META[s.key]?.cat ?? "other") === cat.id);
            if (rows.length === 0) return null;
            return (
              <section key={cat.id}>
                <div style={{ fontSize: 13.5, fontWeight: 700, color: "var(--cv-text-primary)" }}>{cat.title}</div>
                <div style={{ fontSize: 11.5, color: "var(--cv-text-muted)", margin: "2px 0 12px" }}>{cat.caption}</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {rows.map((s) => (
                    <SettingRow key={s.key} setting={s} />
                  ))}
                </div>
              </section>
            );
          })}

          {/* Anything without friendly metadata still shows, so nothing is hidden. */}
          {settings.some((s) => !META[s.key]) && (
            <section>
              <div style={{ fontSize: 13.5, fontWeight: 700, color: "var(--cv-text-primary)" }}>Other</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
                {settings.filter((s) => !META[s.key]).map((s) => (
                  <SettingRow key={s.key} setting={s} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </AppShell>
  );
}

// Suffix shown after the input, and the conversion between what's stored
// (0–1 for percent) and what's shown (a whole-number percentage).
function unitSuffix(meta?: Meta): string {
  if (!meta) return "";
  if (meta.unit === "percent") return "%";
  if (meta.unit === "days") return "days";
  return meta.unitLabel ?? "";
}
const toDisplay = (stored: number, unit?: Unit) => (unit === "percent" ? Math.round(stored * 100) : stored);
const toStored = (shown: number, unit?: Unit) => (unit === "percent" ? Math.round(shown) / 100 : shown);

function SettingRow({ setting }: { setting: PlatformSetting }) {
  const toast = useToast();
  const meta = META[setting.key];
  const isBool = setting.value_type === "boolean";
  const unit = meta?.unit;

  const [value, setValue] = useState<string>(
    isBool ? "" : String(toDisplay(Number(setting.value), unit)),
  );
  const [boolValue, setBoolValue] = useState<boolean>(Boolean(setting.value));
  const [saving, setSaving] = useState(false);

  async function save(v: unknown) {
    setSaving(true);
    try {
      await updateSetting(setting.key, v);
      toast.success("Saved — this takes effect right away.");
    } catch {
      toast.error("Couldn’t save that value. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const title = meta?.label ?? setting.key;
  const blurb = meta?.blurb ?? setting.description;
  const defaultShown =
    unit === "percent"
      ? `${toDisplay(Number(setting.default), unit)}%`
      : `${setting.default}${unit === "days" ? " days" : ""}`;

  return (
    <Card padding="14px 16px">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--cv-text-primary)" }}>{title}</div>
          <div style={{ fontSize: 11.5, color: "var(--cv-text-secondary)", marginTop: 3, lineHeight: 1.5 }}>{blurb}</div>
          {!isBool && (
            <div style={{ fontSize: 10.5, color: "var(--cv-text-muted)", marginTop: 5 }}>Standard setting: {defaultShown}</div>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 7, flexShrink: 0 }}>
          {isBool ? (
            <Toggle checked={boolValue} onChange={(v) => { setBoolValue(v); save(v); }} ariaLabel={title} />
          ) : (
            <>
              <input
                type={setting.value_type === "string" ? "text" : "number"}
                inputMode={setting.value_type === "string" ? undefined : "numeric"}
                step={unit === "percent" ? "1" : setting.value_type === "decimal" ? "0.01" : "1"}
                min={setting.value_type === "string" ? undefined : 0}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                style={{ width: 72, padding: "7px 9px", borderRadius: 7, border: "1px solid var(--cv-input-border)", background: "var(--cv-input-bg)", color: "var(--cv-text-primary)", fontSize: 13, textAlign: "center" }}
              />
              {unitSuffix(meta) && (
                <span style={{ fontSize: 11.5, color: "var(--cv-text-muted)", minWidth: 28 }}>{unitSuffix(meta)}</span>
              )}
              <Button
                onClick={() => {
                  if (setting.value_type === "string") return save(value);
                  const n = Number(value);
                  if (Number.isNaN(n)) return toast.error("Please enter a number.");
                  save(toStored(n, unit));
                }}
                loading={saving}
                style={{ padding: "7px 12px", fontSize: 12 }}
              >
                Save
              </Button>
            </>
          )}
        </div>
      </div>
    </Card>
  );
}
