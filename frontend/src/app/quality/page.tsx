"use client";

import { useEffect, useState } from "react";
import { getQuality, type QualityScorecard, type QualityStandard, type ScopeSel } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { ChartCard, LeagueTable, type LeagueRow } from "@/components/ui/Charts";
import { StatTile } from "@/components/ui/StatTile";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { ScopeFilter } from "@/components/dashboard/ScopeFilter";

// Plain "X in 10" so a non-technical reader can read the share at a glance.
function inWords(rate: number | null): string {
  if (rate == null) return "no data";
  if (rate >= 0.95) return "nearly all";
  if (rate <= 0) return "none";
  const n = Math.round(rate * 10);
  return n <= 0 ? "fewer than 1 in 10" : `${n} in 10`;
}

function scoreStatus(s: number | null): "success" | "warning" | "danger" | "neutral" {
  if (s == null) return "neutral";
  if (s >= 80) return "success";
  if (s >= 60) return "warning";
  return "danger";
}

export default function QualityPage() {
  const [scope, setScope] = useState<ScopeSel>({});
  const [data, setData] = useState<QualityScorecard | null>(null);

  useEffect(() => {
    setData(null);
    getQuality(scope).then(setData).catch(() => setData(null));
  }, [scope]);

  return (
    <AppShell
      title="Quality of care"
      subtitle="Not just whether women come — whether they get the right care each time"
      allowedRoles={["facility_lead", "organisation_user"]}
      action={<ScopeFilter value={scope} onChange={setScope} />}
    >
      {!data ? (
        <div className="cv-stat-grid"><StatTileSkeleton /><StatTileSkeleton /></div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="cv-stat-grid">
            <StatTile
              status={scoreStatus(data.overall_score)}
              label="Overall quality score"
              value={data.overall_score ?? "—"}
              statusLine="out of 100 — the average across every care standard"
            />
          </div>

          {/* What to fix first */}
          {data.gaps.length > 0 && (
            <ChartCard title="What to fix first" subtitle="The care steps most often missed, worst first">
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {data.gaps.map((g) => (
                  <div key={g.key} style={{ display: "flex", gap: 12, alignItems: "flex-start", padding: "10px 12px", border: "1px solid var(--cv-card-border)", borderRadius: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: g.rate != null && g.rate < 0.6 ? "var(--cv-danger-text)" : "var(--cv-warning-text)", flexShrink: 0, minWidth: 64 }}>
                      {inWords(g.rate)}
                    </span>
                    <div>
                      <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>{g.label}</div>
                      <div style={{ fontSize: 11.5, color: "var(--cv-text-secondary)", marginTop: 2 }}>{g.action}</div>
                    </div>
                  </div>
                ))}
              </div>
            </ChartCard>
          )}

          {/* Every standard */}
          <ChartCard
            title="Every care standard"
            subtitle="How often each recommended step was done"
            exportCsv={{
              name: "quality-standards",
              header: ["Care standard", "Share done", "Done", "Out of"],
              rows: data.standards.map((s) => [s.label, s.rate == null ? null : `${Math.round(s.rate * 100)}%`, s.numerator, s.denominator]),
            }}
          >
            <div style={{ display: "flex", flexDirection: "column" }}>
              {data.standards.map((s) => <StandardRow key={s.key} s={s} />)}
            </div>
          </ChartCard>

          {/* By facility */}
          {data.by_facility.length > 1 && (
            <ChartCard
              title="Quality score by facility"
              subtitle="Highest to lowest — where to focus support"
              exportCsv={{
                name: "quality-by-facility",
                header: ["Facility", "Region", "Score"],
                rows: data.by_facility.map((f) => [f.name, f.region, f.score]),
              }}
            >
              <LeagueTable
                rows={data.by_facility.map((f): LeagueRow => ({
                  label: f.name,
                  value: f.score ?? 0,
                  display: f.score == null ? "no data" : `${f.score} / 100`,
                  sublabel: f.region,
                }))}
                maxRows={20}
              />
            </ChartCard>
          )}

          <p style={{ fontSize: 10.5, color: "var(--cv-text-muted)", fontStyle: "italic", margin: 0 }}>
            Based on what was recorded at check-ups and deliveries. A step with no record can’t be counted as done, so a low score can mean weaker care or weaker record-keeping.
          </p>
        </div>
      )}
    </AppShell>
  );
}

function StandardRow({ s }: { s: QualityStandard }) {
  const pct = s.rate == null ? 0 : Math.round(s.rate * 100);
  const color = s.rate == null ? "var(--cv-text-muted)" : s.rate >= 0.9 ? "var(--cv-success-text)" : s.rate >= 0.6 ? "var(--cv-warning-icon)" : "var(--cv-danger-icon)";
  return (
    <div style={{ padding: "12px 0", borderBottom: "1px solid var(--cv-hairline)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, marginBottom: 6 }}>
        <span style={{ fontSize: 12.5, color: "var(--cv-text-secondary)" }}>{s.label}</span>
        <span style={{ flexShrink: 0 }}>
          <strong style={{ fontSize: 13, color: "var(--cv-text-primary)" }}>{inWords(s.rate)}</strong>
          {s.rate != null && <span className="cv-num" style={{ fontSize: 11, color: "var(--cv-text-muted)", marginLeft: 6 }}>({s.numerator} of {s.denominator})</span>}
        </span>
      </div>
      <div style={{ height: 8, borderRadius: 5, background: "var(--cv-hairline)", overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 5 }} />
      </div>
    </div>
  );
}
