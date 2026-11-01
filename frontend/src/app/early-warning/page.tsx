"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getEarlyWarning, type EarlyWarning, type ScopeSel, type Warning,
} from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { ChartCard } from "@/components/ui/Charts";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { ScopeFilter } from "@/components/dashboard/ScopeFilter";

// Each signal gets a plain-language "why this matters" line and a colour.
const TYPE_META: Record<Warning["type"], { tint: string; why: string }> = {
  gone_quiet: {
    tint: "var(--cv-warning-text)",
    why: "A facility that stops reporting can hide real problems — or mean staff need support.",
  },
  activity_falling: {
    tint: "var(--cv-warning-text)",
    why: "Fewer women coming for check-ups now usually means fewer reached later. Worth a call before it slides further.",
  },
  severe_rising: {
    tint: "var(--cv-danger-text)",
    why: "More deaths or stillbirths in recent weeks can be the first sign of a cluster. Review the cases early.",
  },
};

function sevStyle(sev: Warning["severity"]): { color: string; background: string; label: string } {
  if (sev === "high") return { color: "var(--cv-danger-text)", background: "var(--cv-danger-bg)", label: "Look now" };
  if (sev === "medium") return { color: "var(--cv-warning-text)", background: "var(--cv-warning-bg)", label: "Keep an eye on" };
  return { color: "var(--cv-text-muted)", background: "var(--cv-accent-soft)", label: "Minor" };
}

function WatchItem({ w }: { w: Warning }) {
  const sev = sevStyle(w.severity);
  const meta = TYPE_META[w.type];
  return (
    <div
      style={{
        display: "flex", flexDirection: "column", gap: 6,
        padding: "12px 14px", borderRadius: 10,
        border: "1px solid var(--cv-card-border)",
        borderLeft: `4px solid ${meta?.tint ?? "var(--cv-text-muted)"}`,
        background: "var(--cv-card-bg)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 13.5, fontWeight: 650, color: "var(--cv-text-primary)" }}>{w.headline}</div>
          <div style={{ fontSize: 11.5, color: "var(--cv-text-muted)", marginTop: 1 }}>{w.name} · {w.region}</div>
        </div>
        <span style={{ fontSize: 10.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.4, color: sev.color, background: sev.background, padding: "3px 8px", borderRadius: 999, whiteSpace: "nowrap" }}>
          {sev.label}
        </span>
      </div>
      <div style={{ fontSize: 12.5, color: "var(--cv-text-primary)", lineHeight: 1.5 }}>{w.detail}</div>
      {meta && <div style={{ fontSize: 11.5, color: "var(--cv-text-muted)", fontStyle: "italic" }}>{meta.why}</div>}
    </div>
  );
}

export default function EarlyWarningPage() {
  const [scope, setScope] = useState<ScopeSel>({});
  const [data, setData] = useState<EarlyWarning | null>(null);
  const [err, setErr] = useState(false);

  const load = useCallback(() => {
    setErr(false);
    getEarlyWarning(scope).then(setData).catch(() => setErr(true));
  }, [scope]);
  useEffect(() => { load(); }, [load]);

  const watch = data?.watch ?? [];
  const highCount = watch.filter((w) => w.severity === "high").length;

  return (
    <AppShell
      title="Early warning"
      subtitle="Facilities whose numbers are heading the wrong way — so you can act before it becomes harm"
      allowedRoles={["facility_lead", "organisation_user"]}
      action={<ScopeFilter value={scope} onChange={setScope} />}
    >
      {err ? (
        <p style={{ fontSize: 13, color: "var(--cv-danger-text)" }}>Couldn&apos;t load the watch list. Please try again.</p>
      ) : !data ? (
        <div className="cv-stat-grid"><StatTileSkeleton /><StatTileSkeleton /></div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Plain summary line */}
          <div
            style={{
              padding: "14px 16px", borderRadius: 10,
              background: watch.length ? "var(--cv-warning-bg)" : "var(--cv-success-bg)",
              color: watch.length ? "var(--cv-warning-text)" : "var(--cv-success-text)",
              fontSize: 13.5, fontWeight: 600,
            }}
          >
            {watch.length === 0
              ? "All clear — no facilities are heading the wrong way right now."
              : `${watch.length} ${watch.length === 1 ? "facility needs" : "facilities need"} a look` +
                (highCount ? ` — ${highCount} to look at now.` : ".")}
          </div>

          <ChartCard
            title="Watch list"
            subtitle="Each item is a prompt to look, not a verdict. The numbers behind it are shown so you can judge for yourself."
          >
            {watch.length === 0 ? (
              <p style={{ fontSize: 12.5, color: "var(--cv-text-muted)", lineHeight: 1.6 }}>
                Nothing to flag. Reporting is steady, check-ups are holding up, and severe outcomes aren&apos;t climbing
                across the facilities you can see. We&apos;ll surface a facility here the moment that changes.
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {watch.map((w) => <WatchItem key={`${w.facility_id}-${w.type}`} w={w} />)}
              </div>
            )}
          </ChartCard>

          <p style={{ fontSize: 11, color: "var(--cv-text-muted)", lineHeight: 1.6 }}>
            Based on the last {data.window.length} months of records
            {data.window.length ? ` (up to ${data.window[data.window.length - 1]})` : ""}. We only judge facilities
            with enough recent activity for a trend to mean something.
          </p>
        </div>
      )}
    </AppShell>
  );
}
