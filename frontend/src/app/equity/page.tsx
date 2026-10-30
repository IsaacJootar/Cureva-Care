"use client";

import { useCallback, useEffect, useState } from "react";
import { getEquityBreakdown, type EquityBreakdown, type EquityGroup, type ScopeSel } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { SelectField } from "@/components/ui/Field";
import { ChartCard } from "@/components/ui/Charts";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { ScopeFilter } from "@/components/dashboard/ScopeFilter";

// Turn a rate into plain words, ALWAYS out of 10 so groups are directly
// comparable at a glance: 0.89 -> "9 in 10", 0.83 -> "8 in 10", 0.25 -> "3 in 10".
function inWords(rate: number | null): string {
  if (rate == null) return "no data";
  if (rate >= 0.95) return "nearly all";
  if (rate <= 0) return "none";
  const n = Math.round(rate * 10);
  if (n <= 0) return "fewer than 1 in 10";
  return `${n} in 10`;
}

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
  const verb = metric === "screening" ? "are tested" : "get preventives";

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
        {/* Headline in plain words: who's left behind, care is even, or no data. */}
        {gap ? (
          <div style={{ background: gap.points >= 15 ? "var(--cv-warning-bg)" : "var(--cv-accent-soft)", border: "1px solid var(--cv-card-border)", borderRadius: 10, padding: "12px 14px" }}>
            <div style={{ fontSize: 12.5, color: "var(--cv-text-primary)", lineHeight: 1.5 }}>
              <strong>{gap.worst}</strong> are being left behind — only <strong>{inWords(gap.worst_rate)}</strong> {verb},
              {" "}compared with <strong>{inWords(gap.best_rate)}</strong> of <strong>{gap.best}</strong>.
            </div>
          </div>
        ) : data && (data.comparable_groups ?? 0) >= 2 ? (
          <div style={{ background: "var(--cv-success-bg)", border: "1px solid var(--cv-card-border)", borderRadius: 10, padding: "12px 14px", fontSize: 12.5, color: "var(--cv-text-primary)" }}>
            Care looks even — every group gets this about as often. No group is being left behind.
          </div>
        ) : data ? (
          <div style={{ fontSize: 11.5, color: "var(--cv-text-muted)" }}>
            Not enough recorded check-ups in two or more groups to compare yet.
          </div>
        ) : null}

        <ChartCard
          title={data?.metric_label ?? "Coverage"}
          subtitle="How often each group gets this — a group far below the rest is being left behind"
          action={
            <div style={{ width: 200 }}>
              <SelectField id="dimension" label="" value={dimension} onChange={(e) => setDimension(e.target.value)}>
                {dims.map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
              </SelectField>
            </div>
          }
          exportCsv={data ? {
            name: `equity-${dimension}-${metric}`,
            header: ["Group", "Share", "Got it", "Out of"],
            rows: data.groups.map((g) => [g.group, g.rate == null ? null : `${Math.round(g.rate * 100)}%`, g.numerator, g.denominator]),
          } : undefined}
        >
          {!data ? (
            <StatTileSkeleton />
          ) : data.groups.length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No recorded check-ups in this scope yet.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column" }}>
              {data.groups.map((g) => (
                <EquityRow key={g.group} g={g} isWorst={gap?.worst === g.group} />
              ))}
            </div>
          )}
        </ChartCard>

        <p style={{ fontSize: 10.5, color: "var(--cv-text-muted)", fontStyle: "italic", margin: 0 }}>
          Based on what was recorded at check-ups. Very small groups are set aside so a handful of women can’t look like a trend.
        </p>
      </div>
    </AppShell>
  );
}

function EquityRow({ g, isWorst }: { g: EquityGroup; isWorst: boolean }) {
  const pct = g.rate == null ? 0 : Math.round(g.rate * 100);
  const color = g.rate == null ? "var(--cv-text-muted)" : isWorst ? "var(--cv-warning-icon)" : "var(--cv-accent-solid)";
  return (
    <div style={{ padding: "12px 0", borderBottom: "1px solid var(--cv-hairline)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, marginBottom: 6 }}>
        <span style={{ fontSize: 12.5, color: "var(--cv-text-secondary)" }}>
          {g.group}
          {g.low_confidence && <span style={{ color: "var(--cv-text-muted)" }}> · too few to be sure</span>}
          {isWorst && !g.low_confidence && <span style={{ color: "var(--cv-warning-text)", fontWeight: 600 }}> · lowest</span>}
        </span>
        <span style={{ flexShrink: 0 }}>
          <strong style={{ fontSize: 13, color: "var(--cv-text-primary)" }}>{inWords(g.rate)}</strong>
          {g.rate != null && (
            <span className="cv-num" style={{ fontSize: 11, color: "var(--cv-text-muted)", marginLeft: 6 }}>
              ({g.numerator} of {g.denominator})
            </span>
          )}
        </span>
      </div>
      <div style={{ height: 8, borderRadius: 5, background: "var(--cv-hairline)", overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 5 }} />
      </div>
    </div>
  );
}
