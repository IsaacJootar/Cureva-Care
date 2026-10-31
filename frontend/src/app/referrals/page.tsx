"use client";

import { useEffect, useState } from "react";
import { getReferrals, type Referrals, type ScopeSel } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { ChartCard, Funnel, LeagueTable, type LeagueRow } from "@/components/ui/Charts";
import { StatTile } from "@/components/ui/StatTile";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { ScopeFilter } from "@/components/dashboard/ScopeFilter";

export default function ReferralsPage() {
  const [scope, setScope] = useState<ScopeSel>({});
  const [data, setData] = useState<Referrals | null>(null);

  useEffect(() => {
    setData(null);
    getReferrals(scope).then(setData).catch(() => setData(null));
  }, [scope]);

  const unknownShare = data && data.total ? Math.round((data.unknown / data.total) * 100) : 0;

  return (
    <AppShell
      title="Referral outcomes"
      subtitle="When a woman is sent to a bigger facility — did she get there, and what happened?"
      allowedRoles={["facility_lead", "organisation_user"]}
      action={<ScopeFilter value={scope} onChange={setScope} />}
    >
      {!data ? (
        <div className="cv-stat-grid"><StatTileSkeleton /><StatTileSkeleton /><StatTileSkeleton /></div>
      ) : data.total === 0 ? (
        <p style={{ fontSize: 12.5, color: "var(--cv-text-muted)" }}>No referrals recorded in this scope yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="cv-stat-grid">
            <StatTile status="neutral" label="Women referred" value={data.total} />
            <StatTile status="success" label="Confirmed she arrived" value={data.arrived} />
            <StatTile status="neutral" label="Outcome recorded" value={data.outcome_known} />
            <StatTile
              status={data.unknown > 0 ? "danger" : "success"}
              label="We don't know what happened"
              value={data.unknown}
              statusLine={data.unknown > 0 ? `${unknownShare}% of referrals — the loop never closed` : "every referral was followed up"}
            />
          </div>

          <ChartCard title="Following the referral" subtitle="How many we can confirm at each step — a big drop means women are being lost">
            <Funnel stages={data.funnel.map((s) => ({ label: s.label, value: s.value }))} />
          </ChartCard>

          {data.by_facility.length > 1 && (
            <ChartCard
              title="Which facilities close the loop"
              subtitle="Share of referrals where we know the outcome — lowest first, that's where to help"
              exportCsv={{
                name: "referral-loop-closing",
                header: ["Facility", "Region", "Outcome known", "Referrals", "Share"],
                rows: data.by_facility.map((f) => [f.name, f.region, f.outcome_known, f.total, f.rate == null ? null : `${Math.round(f.rate * 100)}%`]),
              }}
            >
              <LeagueTable
                rows={data.by_facility.map((f): LeagueRow => ({
                  label: f.name,
                  value: f.rate ?? 0,
                  display: f.rate == null ? "no data" : `${f.outcome_known} of ${f.total} known`,
                  sublabel: f.region,
                }))}
                maxRows={20}
              />
            </ChartCard>
          )}

          {data.lost.length > 0 && (
            <ChartCard
              title="Referrals that went nowhere"
              subtitle="Sent, but no record she arrived or what happened — follow these up"
              exportCsv={{
                name: "referrals-went-nowhere",
                header: ["Woman", "Reason", "Sent to", "Referred on", "Days waiting"],
                rows: data.lost.map((r) => [r.woman_internal_id, r.reason, r.destination, r.date, r.days_open]),
              }}
            >
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", minWidth: 480, borderCollapse: "collapse", fontSize: 11.5 }}>
                  <thead>
                    <tr style={{ textAlign: "left", color: "var(--cv-text-muted)" }}>
                      <th style={{ padding: "6px 8px" }}>Woman</th>
                      <th style={{ padding: "6px 8px" }}>Reason</th>
                      <th style={{ padding: "6px 8px" }}>Sent to</th>
                      <th style={{ padding: "6px 8px" }}>Days waiting</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.lost.slice(0, 50).map((r, i) => (
                      <tr key={i} style={{ borderTop: "1px solid var(--cv-hairline)" }}>
                        <td style={{ padding: "6px 8px", color: "var(--cv-text-primary)", fontWeight: 600 }}>{r.woman_internal_id}</td>
                        <td style={{ padding: "6px 8px", color: "var(--cv-text-secondary)" }}>{r.reason ?? "—"}</td>
                        <td style={{ padding: "6px 8px", color: "var(--cv-text-secondary)" }}>{r.destination ?? "—"}</td>
                        <td className="cv-num" style={{ padding: "6px 8px" }}>{r.days_open ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ChartCard>
          )}

          {data.destinations.length > 0 && (
            <ChartCard title="Where women are sent" subtitle="The facilities they're referred to most">
              <LeagueTable
                rows={data.destinations.map((d): LeagueRow => ({ label: d.name, value: d.count, display: `${d.count}` }))}
                maxRows={10}
              />
            </ChartCard>
          )}

          <p style={{ fontSize: 10.5, color: "var(--cv-text-muted)", fontStyle: "italic", margin: 0 }}>
            Recording whether a woman arrived is optional — where it isn’t captured, the referral counts as “we don’t know,” which is exactly the gap to close.
          </p>
        </div>
      )}
    </AppShell>
  );
}
