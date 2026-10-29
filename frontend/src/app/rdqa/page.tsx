"use client";

import { useEffect, useState } from "react";
import { getRdqaScorecard, type RdqaScorecard } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { ChartCard } from "@/components/ui/Charts";
import { StatTile } from "@/components/ui/StatTile";

const pct = (v: number | null | undefined) => (v == null ? "—" : `${Math.round(v * 100)}%`);

function scoreColor(s: number | null) {
  if (s == null) return "var(--cv-text-muted)";
  if (s >= 80) return "var(--cv-success-text)";
  if (s >= 60) return "var(--cv-warning-text)";
  return "var(--cv-danger-text)";
}

export default function ReportingReliabilityPage() {
  const [sc, setSc] = useState<RdqaScorecard | null>(null);

  useEffect(() => {
    getRdqaScorecard().then(setSc).catch(() => setSc(null));
  }, []);

  const o = sc?.overall ?? {};
  // Average completeness across assessed facilities (frontend roll-up) — a
  // buyer-facing "how filled-in are the records" read, not our AI's confidence.
  const completeness = (() => {
    const vals = (sc?.facilities ?? [])
      .map((f) => f.completeness)
      .filter((v): v is number => v != null);
    if (vals.length === 0) return null;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  })();

  return (
    <AppShell
      title="Reporting reliability"
      subtitle="Which facilities report completely and on time"
      allowedRoles={["facility_lead", "organisation_user"]}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
          <StatTile status={o.mean_score != null && o.mean_score >= 80 ? "success" : "warning"} label="Reliability score" value={o.mean_score ?? "—"} />
          <StatTile status="neutral" label="Fields filled in (avg)" value={pct(completeness)} />
          <StatTile status="neutral" label="Facilities assessed" value={o.facilities_assessed ?? 0} />
          <StatTile status={(o.total_open_flags ?? 0) > 0 ? "warning" : "success"} label="Unresolved column issues" value={o.total_open_flags ?? 0} />
        </div>

        <ChartCard
          title="By facility"
          subtitle="Who reports completely and on time — download the full table"
          exportCsv={sc ? {
            name: "reporting-reliability",
            header: ["Facility", "Region", "Rows", "Score", "Completeness", "Implausible rate", "Open flags", "Avg days to publish"],
            rows: sc.facilities.map((f) => [f.name, f.region, f.rows, f.score, pct(f.completeness), pct(f.implausible_rate), f.open_template_flags, f.avg_days_to_publish]),
          } : undefined}
        >
          {!sc || sc.facilities.length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No published data to assess yet.</p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11.5 }}>
                <thead>
                  <tr style={{ textAlign: "left", color: "var(--cv-text-muted)" }}>
                    <th style={{ padding: "6px 8px" }}>Facility</th>
                    <th style={{ padding: "6px 8px" }}>Score</th>
                    <th style={{ padding: "6px 8px" }}>Fields filled in</th>
                    <th style={{ padding: "6px 8px" }}>Odd values</th>
                    <th style={{ padding: "6px 8px" }}>Column issues</th>
                    <th style={{ padding: "6px 8px" }}>Days to publish</th>
                  </tr>
                </thead>
                <tbody>
                  {sc.facilities.map((f) => (
                    <tr key={f.facility_id} style={{ borderTop: "1px solid var(--cv-hairline)" }}>
                      <td style={{ padding: "6px 8px", color: "var(--cv-text-primary)", fontWeight: 600 }}>{f.name}<div style={{ fontSize: 10, color: "var(--cv-text-muted)" }}>{f.region}</div></td>
                      <td className="cv-num" style={{ padding: "6px 8px", fontWeight: 700, color: scoreColor(f.score) }}>{f.score ?? "—"}</td>
                      <td className="cv-num" style={{ padding: "6px 8px" }}>{pct(f.completeness)}</td>
                      <td className="cv-num" style={{ padding: "6px 8px" }}>{pct(f.implausible_rate)}</td>
                      <td className="cv-num" style={{ padding: "6px 8px" }}>{f.open_template_flags}</td>
                      <td className="cv-num" style={{ padding: "6px 8px" }}>{f.avg_days_to_publish ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ChartCard>
      </div>
    </AppShell>
  );
}
