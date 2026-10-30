"use client";

import { useEffect, useMemo, useState } from "react";
import { getSummary, type ScopeSel, type Summary } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { BarGroup, ChartPanel } from "@/components/ui/Charts";
import { ScopeFilter } from "@/components/dashboard/ScopeFilter";
import { SelectField } from "@/components/ui/Field";
import { StatTile } from "@/components/ui/StatTile";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { HeartPulseIcon } from "@/components/icons";

type Period = "all" | "year" | "90d";
const iso = (d: Date) => d.toISOString().slice(0, 10);

function periodRange(p: Period): { from?: string; to?: string; label: string } {
  const now = new Date();
  if (p === "year") return { from: `${now.getFullYear()}-01-01`, to: iso(now), label: `this year (${now.getFullYear()})` };
  if (p === "90d") return { from: iso(new Date(Date.now() - 90 * 86400000)), to: iso(now), label: "the last 3 months" };
  return { label: "all recorded dates" };
}

export default function OutcomesPage() {
  const [period, setPeriod] = useState<Period>("all");
  const [scope, setScope] = useState<ScopeSel>({});
  const [s, setS] = useState<Summary | null>(null);
  const range = useMemo(() => periodRange(period), [period]);

  useEffect(() => {
    setS(null);
    getSummary(range.from, range.to, scope).then(setS).catch(() => setS(null));
  }, [range.from, range.to, scope]);

  const facilities = s?.scope?.facility_count ?? 0;

  return (
    <AppShell
      title="Outcomes"
      subtitle="Documented maternal, birth, and newborn outcomes"
      allowedRoles={["facility_lead", "organisation_user"]}
      action={
        <div style={{ display: "flex", gap: 8 }}>
          <ScopeFilter value={scope} onChange={setScope} />
          <div style={{ width: 160 }}>
            <SelectField id="period" label="" value={period} onChange={(e) => setPeriod(e.target.value as Period)}>
              <option value="all">All recorded dates</option>
              <option value="year">This year</option>
              <option value="90d">Last 3 months</option>
            </SelectField>
          </div>
        </div>
      }
    >
      {!s ? (
        <div className="cv-stat-grid" style={{ maxWidth: 900, margin: "0 auto" }}>
          {Array.from({ length: 4 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 900, margin: "0 auto" }}>
          <div style={{ fontSize: 11.5, color: "var(--cv-text-muted)" }}>
            Across <strong>{facilities}</strong> facilit{facilities === 1 ? "y" : "ies"} · {range.label}.
          </div>
          <div className="cv-stat-grid">
            <StatTile status="success" icon={<HeartPulseIcon size={14} />} label="Live births" value={s.outcomes.live_births} />
            <StatTile status={s.outcomes.still_births > 0 ? "danger" : "success"} icon={<HeartPulseIcon size={14} />} label="Stillbirths" value={s.outcomes.still_births} />
            <StatTile status={s.outcomes.maternal_deaths > 0 ? "danger" : "success"} icon={<HeartPulseIcon size={14} />} label="Maternal deaths" value={s.outcomes.maternal_deaths} />
            <StatTile status={s.outcomes.low_birth_weight > 0 ? "warning" : "neutral"} icon={<HeartPulseIcon size={14} />} label="Low birth weight" value={s.outcomes.low_birth_weight} statusLine="< 2.5 kg" />
          </div>
          <ChartPanel title="Birth outcome distribution">
            <BarGroup data={[
              { label: "Live births", value: s.outcomes.live_births, status: "success" },
              { label: "Stillbirths", value: s.outcomes.still_births, status: "danger" },
              { label: "Low birth wt.", value: s.outcomes.low_birth_weight, status: "warning" },
            ]} />
            <p style={{ fontSize: 11, color: "var(--cv-text-muted)", marginTop: 12 }}>
              Counts of outcomes facilities actually recorded. Blank entries are left blank, never guessed.
            </p>
          </ChartPanel>
        </div>
      )}
    </AppShell>
  );
}
