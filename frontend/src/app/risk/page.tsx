"use client";

import { useEffect, useState } from "react";
import { getAlerts, getRiskPyramid, getRiskRegistry, type Alerts, type RiskPyramid, type RiskRegistry, type ScopeSel } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { ChartCard, StackedBars } from "@/components/ui/Charts";
import { ScopeFilter } from "@/components/dashboard/ScopeFilter";
import { AlertTriangleIcon } from "@/components/icons";

const TIER_COLOR: Record<string, string> = {
  High: "var(--cv-danger-icon)",
  Moderate: "var(--cv-warning-icon)",
  "None recorded": "var(--cv-button-disabled-bg)",
};
const SEV_COLOR: Record<string, string> = { high: "var(--cv-danger-text)", medium: "var(--cv-warning-text)", low: "var(--cv-text-muted)" };

export default function RiskPage() {
  const [pyr, setPyr] = useState<RiskPyramid | null>(null);
  const [reg, setReg] = useState<RiskRegistry | null>(null);
  const [alerts, setAlerts] = useState<Alerts | null>(null);
  const [scope, setScope] = useState<ScopeSel>({});

  useEffect(() => {
    setPyr(null); setReg(null); setAlerts(null);
    getRiskPyramid(scope).then(setPyr).catch(() => setPyr(null));
    getRiskRegistry(undefined, scope).then(setReg).catch(() => setReg(null));
    getAlerts(scope).then(setAlerts).catch(() => setAlerts(null));
  }, [scope]);

  const aggregate = reg?.access_level === "aggregate";
  const tiers = pyr?.tiers ?? {};

  return (
    <AppShell
      title="Risk & alerts"
      subtitle="Open pregnancies to follow up — as of today"
      allowedRoles={["facility_lead", "organisation_user"]}
      action={<ScopeFilter value={scope} onChange={setScope} />}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {pyr && (
          <div style={{ fontSize: 11.5, color: "var(--cv-text-muted)" }}>
            Combined across all <strong>{pyr.facility_count ?? 0}</strong> facilit{(pyr.facility_count ?? 0) === 1 ? "y" : "ies"} in your scope · as of today.
          </div>
        )}
        <ChartCard title="Alerts" subtitle="Based on recorded check-ups · WHO guidance · not a diagnosis">
          {!alerts ? (
            <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>Loading…</p>
          ) : alerts.alerts.length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No active alerts. 🎉</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {alerts.alerts.map((a, i) => (
                <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "10px 12px", border: "1px solid var(--cv-card-border)", borderRadius: 8 }}>
                  <span style={{ color: SEV_COLOR[a.severity], flexShrink: 0, marginTop: 1 }}><AlertTriangleIcon size={16} /></span>
                  <div>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>{a.title}</div>
                    <div style={{ fontSize: 11.5, color: "var(--cv-text-secondary)", marginTop: 2 }}>{a.detail}</div>
                  </div>
                  <span style={{ marginLeft: "auto", fontSize: 10, textTransform: "uppercase", fontWeight: 700, color: SEV_COLOR[a.severity] }}>{a.severity}</span>
                </div>
              ))}
            </div>
          )}
        </ChartCard>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: 16 }}>
          <ChartCard title="Risk levels" subtitle="Pregnancies in progress now, by risk level">
            {!pyr || pyr.total === 0 ? (
              <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No active pregnancies in scope.</p>
            ) : (
              <StackedBars rows={(["High", "Moderate", "None recorded"]).map((t) => ({
                label: t,
                segments: [{ label: t, value: tiers[t] ?? 0, color: TIER_COLOR[t] }],
              }))} />
            )}
          </ChartCard>

          <ChartCard
            title="Pregnancies to watch"
            subtitle="Open pregnancies, highest risk first"
            exportCsv={reg && !aggregate ? {
              name: "risk-registry",
              header: ["Woman", "Risk level", "Warning signs", "Registered", "Last check-up", "Days since last check-up"],
              rows: reg.rows.map((r) => [r.woman?.name ?? "(hidden)", r.tier, r.markers.join("; "), r.booking_date, r.last_anc, r.days_since_anc]),
            } : undefined}
          >
            {!reg ? (
              <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>Loading…</p>
            ) : aggregate ? (
              <p style={{ fontSize: 11.5, color: "var(--cv-text-muted)" }}><strong className="cv-num">{reg.count}</strong> at-risk pregnancies. Your access is totals only, so individual pregnancies aren’t listed.</p>
            ) : reg.rows.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No pregnancies with a recorded risk marker. 🎉</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", minWidth: 480, borderCollapse: "collapse", fontSize: 11.5 }}>
                  <thead>
                    <tr style={{ textAlign: "left", color: "var(--cv-text-muted)" }}>
                      <th style={{ padding: "6px 8px" }}>Woman</th>
                      <th style={{ padding: "6px 8px" }}>Risk level</th>
                      <th style={{ padding: "6px 8px" }}>Warning signs recorded</th>
                      <th style={{ padding: "6px 8px" }}>Days since last check-up</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reg.rows.slice(0, 60).map((r) => (
                      <tr key={r.episode_id} style={{ borderTop: "1px solid var(--cv-hairline)" }}>
                        <td style={{ padding: "6px 8px", color: "var(--cv-text-primary)", fontWeight: 600 }}>{r.woman?.name ?? "—"}</td>
                        <td style={{ padding: "6px 8px" }}><span style={{ color: TIER_COLOR[r.tier], fontWeight: 600 }}>{r.tier}</span></td>
                        <td style={{ padding: "6px 8px", color: "var(--cv-text-secondary)" }}>{r.markers.join(", ")}</td>
                        <td className="cv-num" style={{ padding: "6px 8px" }}>{r.days_since_anc ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </ChartCard>
        </div>
      </div>
    </AppShell>
  );
}
