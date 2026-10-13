"use client";

import { useEffect, useState } from "react";
import { getSummary, type Summary } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { BarGroup, ChartPanel } from "@/components/ui/Charts";
import { StatTile } from "@/components/ui/StatTile";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { HeartPulseIcon } from "@/components/icons";

export default function OutcomesPage() {
  const [s, setS] = useState<Summary | null>(null);
  useEffect(() => {
    getSummary().then(setS).catch(() => setS(null));
  }, []);

  return (
    <AppShell title="Outcomes" subtitle="Documented maternal, birth, and newborn outcomes" allowedRoles={["facility_lead", "organisation_user"]}>
      {!s ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
          {Array.from({ length: 4 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 900 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
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
              Counts of documented outcomes only — missing outcomes are never inferred (rule #6). Cureva Care reports recorded activity, not population rates.
            </p>
          </ChartPanel>
        </div>
      )}
    </AppShell>
  );
}
