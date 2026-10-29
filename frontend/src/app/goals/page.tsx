"use client";

import { useEffect, useState } from "react";
import { getGoals, type Goal } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { ChartCard } from "@/components/ui/Charts";
import { StatTileSkeleton } from "@/components/ui/Feedback";

export default function GoalsPage() {
  const [goals, setGoals] = useState<Goal[] | null>(null);

  useEffect(() => {
    getGoals().then((d) => setGoals(d.goals)).catch(() => setGoals([]));
  }, []);

  const onTrack = (goals ?? []).filter((g) => g.on_track === true).length;
  const assessable = (goals ?? []).filter((g) => g.on_track !== null).length;

  return (
    <AppShell
      title="Goals & targets"
      subtitle="Progress toward your programme's coverage goals"
      allowedRoles={["facility_lead", "organisation_user"]}
    >
      {!goals ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {Array.from({ length: 3 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ fontSize: 12, color: "var(--cv-text-secondary)", background: "var(--cv-accent-soft)", border: "1px solid var(--cv-card-border)", borderRadius: 9, padding: "10px 13px" }}>
            {assessable === 0
              ? "No data yet to measure against your goals."
              : <><strong>{onTrack} of {assessable}</strong> goals are on track.</>}
          </div>

          <ChartCard title="Progress to targets" subtitle="Where you stand against each goal, and how far to the target line">
            {goals.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No active goals. An administrator sets these under Goals & targets.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {goals.map((g) => <GoalBar key={g.key} goal={g} />)}
              </div>
            )}
          </ChartCard>
        </div>
      )}
    </AppShell>
  );
}

function GoalBar({ goal }: { goal: Goal }) {
  const current = goal.current_pct;
  const hasData = current != null;
  const ok = goal.on_track === true;
  const barColor = !hasData ? "var(--cv-text-muted)" : ok ? "var(--cv-success-text)" : "var(--cv-warning-text)";

  return (
    <div style={{ padding: "12px 0", borderBottom: "1px solid var(--cv-hairline)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6, gap: 10 }}>
        <span style={{ fontSize: 12.5, color: "var(--cv-text-secondary)" }}>{goal.label}</span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
          <span className="cv-num" style={{ fontSize: 13, fontWeight: 700, color: "var(--cv-text-primary)" }}>
            {hasData ? `${current}%` : "no data"}
            {goal.denominator != null && hasData && (
              <span style={{ fontSize: 11, color: "var(--cv-text-muted)", fontWeight: 400 }}> ({goal.numerator}/{goal.denominator})</span>
            )}
          </span>
          {hasData && (
            <span style={{ fontSize: 10.5, fontWeight: 600, padding: "2px 8px", borderRadius: 20, color: ok ? "var(--cv-success-text)" : "var(--cv-warning-text)", background: ok ? "var(--cv-success-bg)" : "var(--cv-warning-bg)" }}>
              {ok ? "On track" : "Below target"}
            </span>
          )}
        </span>
      </div>
      {/* Track with current fill + a target marker line */}
      <div style={{ position: "relative", height: 8, borderRadius: 5, background: "var(--cv-hairline)", overflow: "visible" }}>
        <div style={{ position: "absolute", inset: 0, width: `${Math.min(100, current ?? 0)}%`, background: barColor, borderRadius: 5 }} />
        <div
          title={`Target: ${goal.target_pct}%`}
          style={{ position: "absolute", top: -3, bottom: -3, left: `calc(${Math.min(100, goal.target_pct)}% - 1px)`, width: 2, background: "var(--cv-text-primary)", borderRadius: 2 }}
        />
      </div>
      <div style={{ fontSize: 10.5, color: "var(--cv-text-muted)", marginTop: 4, display: "flex", justifyContent: "space-between" }}>
        <span>{goal.help}</span>
        <span style={{ flexShrink: 0, marginLeft: 10 }}>Target {goal.target_pct}%</span>
      </div>
    </div>
  );
}
