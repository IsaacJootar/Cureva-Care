"use client";

import { useCallback, useEffect, useState } from "react";
import { getEquityBreakdown, type EquityBreakdown, type ScopeSel } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { SelectField } from "@/components/ui/Field";
import { ChartCard, MetricMeter } from "@/components/ui/Charts";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { ScopeFilter } from "@/components/dashboard/ScopeFilter";

export default function EquityPage() {
  const [dimension, setDimension] = useState("parity");
  const [metric, setMetric] = useState("screening");
  const [scope, setScope] = useState<ScopeSel>({});
  const [data, setData] = useState<EquityBreakdown | null>(null);

  const load = useCallback(() => {
    setData(null);
    getEquityBreakdown({ dimension, metric, scope }).then(setData).catch(() => setData(null));
  }, [dimension, metric, scope]);
  useEffect(() => { load(); }, [load]);

  const dims = data?.dimensions ?? [
    { key: "parity", label: "By number of past births" },
    { key: "age", label: "By mother's age" },
    { key: "area", label: "By area (LGA)" },
  ];
  const metrics = data?.metrics ?? [
    { key: "screening", label: "Tested (HIV, syphilis, anaemia)" },
    { key: "intervention", label: "Got preventives (iron, tetanus, malaria)" },
  ];
  const gap = data?.gap ?? null;

  return (
    <AppShell
      title="Equity"
      subtitle="Is every group getting the same care — or is one being left behind?"
      allowedRoles={["facility_lead", "organisation_user"]}
      action={
        <div style={{ display: "flex", gap: 8 }}>
          <ScopeFilter value={scope} onChange={setScope} />
          <div style={{ width: 230 }}>
            <SelectField id="metric" label="" value={metric} onChange={(e) => setMetric(e.target.value)}>
              {metrics.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
            </SelectField>
          </div>
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Headline: a real gap, "care looks even", or not enough data. */}
        {gap ? (
          <div style={{ background: gap.points >= 15 ? "var(--cv-warning-bg)" : "var(--cv-accent-soft)", border: "1px solid var(--cv-card-border)", borderRadius: 10, padding: "12px 14px" }}>
            <div style={{ fontSize: 12.5, color: "var(--cv-text-primary)" }}>
              <strong>{gap.worst}</strong> are getting the least: only {Math.round(gap.worst_rate * 100)}%
              {" "}vs {Math.round(gap.best_rate * 100)}% for <strong>{gap.best}</strong> — a <strong>{gap.points}-point gap</strong>.
            </div>
          </div>
        ) : data && (data.comparable_groups ?? 0) >= 2 ? (
          <div style={{ background: "var(--cv-success-bg)", border: "1px solid var(--cv-card-border)", borderRadius: 10, padding: "12px 14px", fontSize: 12.5, color: "var(--cv-text-primary)" }}>
            Care looks even across these groups — no group is clearly being left behind.
          </div>
        ) : data ? (
          <div style={{ fontSize: 11.5, color: "var(--cv-text-muted)" }}>
            Not enough recorded check-ups in two or more groups to compare yet.
          </div>
        ) : null}

        <ChartCard
          title={data?.metric_label ?? "Coverage"}
          subtitle="Each group’s share — a wide spread means care isn’t reaching everyone equally"
          action={
            <div style={{ width: 200 }}>
              <SelectField id="dimension" label="" value={dimension} onChange={(e) => setDimension(e.target.value)}>
                {dims.map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
              </SelectField>
            </div>
          }
          exportCsv={data ? {
            name: `equity-${dimension}-${metric}`,
            header: ["Group", "Rate", "Numerator", "Denominator"],
            rows: data.groups.map((g) => [g.group, g.rate, g.numerator, g.denominator]),
          } : undefined}
        >
          {!data ? (
            <StatTileSkeleton />
          ) : data.groups.length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No recorded check-ups in this scope yet.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {data.groups.map((g) => (
                <MetricMeter
                  key={g.group}
                  label={`${g.group}${g.low_confidence ? " · small group" : ""}`}
                  ratio={{ numerator: g.numerator, denominator: g.denominator, rate: g.rate }}
                />
              ))}
            </div>
          )}
        </ChartCard>

        <p style={{ fontSize: 10.5, color: "var(--cv-text-muted)", fontStyle: "italic", margin: 0 }}>
          Based on what was recorded at check-ups; groups with very few check-ups are flagged and left out of the gap.
        </p>
      </div>
    </AppShell>
  );
}
