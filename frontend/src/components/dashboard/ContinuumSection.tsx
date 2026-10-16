"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getCohorts, getContinuumFunnel, getDropoff,
  type CareFunnel, type Cohorts, type Dropoff,
} from "@/lib/dashboard";
import { ChartCard, LineChart, type LineSeries } from "@/components/ui/Charts";

// WS3 — the "who fell through" view: a care funnel whose drop-offs open an
// access-scoped line-list of named women to follow up, plus booking-cohort
// retention over time.

export function ContinuumSection() {
  const [funnel, setFunnel] = useState<CareFunnel | null>(null);
  const [cohorts, setCohorts] = useState<Cohorts | null>(null);
  const [kind, setKind] = useState("delivered_no_pnc");
  const [drop, setDrop] = useState<Dropoff | null>(null);

  useEffect(() => {
    getContinuumFunnel().then(setFunnel).catch(() => setFunnel(null));
    getCohorts().then(setCohorts).catch(() => setCohorts(null));
  }, []);

  const loadDrop = useCallback(() => {
    getDropoff(kind).then(setDrop).catch(() => setDrop(null));
  }, [kind]);
  useEffect(() => { loadDrop(); }, [loadDrop]);

  const total = funnel?.total ?? 0;
  const aggregate = drop?.access_level === "aggregate";

  const cohortSeries: LineSeries[] = cohorts
    ? Object.values(cohorts.series).map((s) => ({ name: s.label, points: s.points.map((p) => ({ x: p.x, y: p.rate == null ? null : Math.round(p.rate * 100) })) }))
    : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <ChartCard
        title="Care-journey funnel"
        subtitle="Women at each step of the continuum — and how many drop off between steps"
        note="Only linked episodes count toward a cross-register step; a gap is a follow-up opportunity, not an error."
        exportCsv={{
          name: "care-funnel",
          header: ["Step", "Women", "Dropped from previous", "Share of booked"],
          rows: (funnel?.steps ?? []).map((s) => [s.label, s.value, s.drop_from_previous, s.share_of_booked == null ? null : `${Math.round(s.share_of_booked * 100)}%`]),
        }}
      >
        {!funnel || funnel.steps.length === 0 ? (
          <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No booked episodes yet.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {funnel.steps.map((st, i) => {
              const pct = total ? Math.round((st.value / total) * 100) : 0;
              return (
                <div key={st.label}>
                  {i > 0 && st.drop_from_previous > 0 && (
                    <div style={{ fontSize: 10.5, color: "var(--cv-danger-text)", margin: "0 0 4px 2px" }}>
                      ↓ {st.drop_from_previous} dropped
                    </div>
                  )}
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, marginBottom: 4 }}>
                    <span style={{ color: "var(--cv-text-secondary)" }}>{st.label}</span>
                    <span className="cv-num" style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>
                      {st.value} <span style={{ color: "var(--cv-text-muted)", fontWeight: 400 }}>({pct}%)</span>
                    </span>
                  </div>
                  <div style={{ height: 22, borderRadius: 6, background: "var(--cv-button-disabled-bg)", overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${Math.max(pct, 2)}%`, background: "var(--cv-accent-gradient)", borderRadius: 6 }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </ChartCard>

      <ChartCard
        title="Follow-up list — who fell through"
        subtitle="Download a named list of women to follow up at a drop-off point"
        note="Access-scoped: aggregate viewers see counts only; de-identified hides names. Recorded activity, not population rates."
        action={
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            style={{ fontSize: 11.5, padding: "4px 8px", borderRadius: 6, border: "1px solid var(--cv-input-border)", background: "var(--cv-input-bg)", color: "var(--cv-text-primary)" }}
          >
            {(drop?.available_kinds ?? [{ key: "delivered_no_pnc", label: "Delivered but no postnatal contact" }]).map((k) => (
              <option key={k.key} value={k.key}>{k.label}</option>
            ))}
          </select>
        }
        exportCsv={drop && !aggregate ? {
          name: `followup-${kind}`,
          header: ["Woman", "Internal ID", "Booking date", "ANC contacts", "Delivered on", "Days since"],
          rows: drop.rows.map((r) => [r.woman?.name ?? "(hidden)", r.woman_internal_id, r.booking_date, r.anc_contacts, r.delivered_on, r.days_since]),
        } : undefined}
      >
        {!drop ? (
          <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>Loading…</p>
        ) : (
          <>
            <div style={{ fontSize: 12.5, color: "var(--cv-text-primary)", marginBottom: 10 }}>
              <span className="cv-num" style={{ fontWeight: 700, fontSize: 18 }}>{drop.count}</span> {drop.label.toLowerCase()}
            </div>
            {aggregate ? (
              <p style={{ fontSize: 11.5, color: "var(--cv-text-muted)" }}>Your access level shows counts only — the case list is not available.</p>
            ) : drop.rows.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No women at this drop-off point. 🎉</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11.5 }}>
                  <thead>
                    <tr style={{ textAlign: "left", color: "var(--cv-text-muted)" }}>
                      <th style={{ padding: "6px 8px" }}>Woman</th>
                      <th style={{ padding: "6px 8px" }}>Booked</th>
                      <th style={{ padding: "6px 8px" }}>ANC</th>
                      <th style={{ padding: "6px 8px" }}>Delivered</th>
                      <th style={{ padding: "6px 8px" }}>Days since</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drop.rows.slice(0, 50).map((r) => (
                      <tr key={r.episode_id} style={{ borderTop: "1px solid var(--cv-hairline)" }}>
                        <td style={{ padding: "6px 8px", color: "var(--cv-text-primary)", fontWeight: 600 }}>{r.woman?.name ?? "—"}</td>
                        <td style={{ padding: "6px 8px" }}>{r.booking_date ?? "—"}</td>
                        <td className="cv-num" style={{ padding: "6px 8px" }}>{r.anc_contacts}</td>
                        <td style={{ padding: "6px 8px" }}>{r.delivered_on ?? "—"}</td>
                        <td className="cv-num" style={{ padding: "6px 8px" }}>{r.days_since ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </ChartCard>

      <ChartCard
        title="Cohort retention"
        subtitle="Of women who booked each month, the share reaching 4+ ANC, delivery and postnatal care"
        note="Each cohort's denominator is its own bookings. Recorded activity, not population rates."
        exportCsv={cohorts ? {
          name: "cohort-retention",
          header: ["Booking month", ...Object.values(cohorts.series).map((s) => s.label)],
          rows: cohorts.cohorts.map((c, i) => [c, ...Object.values(cohorts.series).map((s) => {
            const p = s.points[i];
            return p && p.rate != null ? `${Math.round(p.rate * 100)}%` : null;
          })]),
        } : undefined}
      >
        {!cohorts || cohorts.cohorts.length === 0 ? (
          <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>Cohort curves appear once bookings span more than one month.</p>
        ) : (
          <LineChart series={cohortSeries} unit="percent" />
        )}
      </ChartCard>
    </div>
  );
}
