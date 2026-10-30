"use client";

import { useCallback, useEffect, useState } from "react";
import { getTrends, type ScopeSel, type TrendMetric, type Trends } from "@/lib/dashboard";
import { ChartCard, DeltaBadge, LineChart, type LineSeries } from "@/components/ui/Charts";

// WS1 — Time & Trends. Turns the point-in-time metrics into trend lines with a
// month/week toggle, per-metric deltas, and CSV/PNG export. All rate series are
// shown as percentages with their denominators preserved in the export.

function toSeries(m: TrendMetric | undefined): LineSeries | null {
  if (!m) return null;
  return {
    name: m.label,
    points: m.points.map((p) =>
      "value" in p ? { x: p.x, y: p.value } : { x: p.x, y: p.rate == null ? null : Math.round(p.rate * 100) },
    ),
  };
}

function csvFor(t: Trends, keys: string[]) {
  const header = ["Period", ...keys.map((k) => t.metrics[k]?.label ?? k)];
  const rows = t.buckets.map((b, i) =>
    [b, ...keys.map((k) => {
      const p = t.metrics[k]?.points[i];
      if (!p) return null;
      return "value" in p ? p.value : p.rate == null ? null : `${Math.round(p.rate * 100)}% (${p.numerator}/${p.denominator})`;
    })],
  );
  return { header, rows };
}

const NOTE = "Based on what facilities have recorded, not population estimates.";

export function TrendsPanel({ scope }: { scope?: ScopeSel } = {}) {
  const [bucket, setBucket] = useState<"month" | "week">("month");
  const [data, setData] = useState<Trends | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    getTrends(bucket, undefined, undefined, scope).then(setData).catch(() => setData(null)).finally(() => setLoading(false));
  }, [bucket, scope]);

  useEffect(() => { load(); }, [load]);

  const hasData = data && data.buckets.length > 0;

  const toggle = (
    <div style={{ display: "inline-flex", background: "var(--cv-bg)", borderRadius: "var(--cv-radius-pill)", padding: 2, border: "1px solid var(--cv-hairline)" }}>
      {(["month", "week"] as const).map((b) => (
        <button
          key={b}
          onClick={() => setBucket(b)}
          style={{
            padding: "4px 12px", borderRadius: "var(--cv-radius-pill)", border: "none", cursor: "pointer",
            fontSize: 11.5, fontWeight: 600, textTransform: "capitalize",
            background: bucket === b ? "var(--cv-accent-solid)" : "transparent",
            color: bucket === b ? "#fff" : "var(--cv-text-secondary)",
          }}
        >
          {b}ly
        </button>
      ))}
    </div>
  );

  if (loading) return <p style={{ fontSize: 12.5, color: "var(--cv-text-muted)" }}>Loading trends…</p>;
  if (!hasData) {
    return (
      <div style={{ background: "var(--cv-card-bg)", border: "1px solid var(--cv-card-border)", borderRadius: "var(--cv-radius-card)", padding: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: 0 }}>Trends over time</h2>
          {toggle}
        </div>
        <p style={{ fontSize: 12.5, color: "var(--cv-text-muted)", marginTop: 14 }}>
          No dated activity yet. Trend lines appear once published intakes span more than one {bucket}.
        </p>
      </div>
    );
  }

  const activity = ["anc_contacts", "deliveries", "pnc_contacts"].map((k) => toSeries(data!.metrics[k])).filter((s): s is LineSeries => !!s);
  const coverage = ["early_anc_booking", "screening_coverage", "intervention_coverage", "referral_closure"].map((k) => toSeries(data!.metrics[k])).filter((s): s is LineSeries => !!s);
  const outcomes = ["live_births", "still_births", "maternal_deaths"].map((k) => toSeries(data!.metrics[k])).filter((s): s is LineSeries => !!s);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ fontSize: 15, color: "var(--cv-text-primary)", margin: 0 }}>Trends over time</h2>
        {toggle}
      </div>

      <ChartCard
        title="Activity over time"
        subtitle="Pregnancy check-ups, births & after-birth check-ups per period"
        note={NOTE}
        action={<DeltaBadge delta={data!.deltas.deliveries ?? null} unit="" />}
        exportCsv={{ name: "activity-trend", ...csvFor(data!, ["anc_contacts", "deliveries", "pnc_contacts"]) }}
      >
        <LineChart series={activity} unit="count" />
      </ChartCard>

      <ChartCard
        title="Quality of care over time"
        subtitle="Early registration, testing, preventives & referral follow-up (%)"
        note={NOTE}
        exportCsv={{ name: "coverage-trend", ...csvFor(data!, ["early_anc_booking", "screening_coverage", "intervention_coverage", "referral_closure"]) }}
      >
        <LineChart series={coverage} unit="percent" />
      </ChartCard>

      <ChartCard
        title="Outcomes over time"
        subtitle="Live births, stillbirths & mothers who died per period"
        note={NOTE}
        action={<DeltaBadge delta={data!.deltas.maternal_deaths ?? null} unit="" invert />}
        exportCsv={{ name: "outcomes-trend", ...csvFor(data!, ["live_births", "still_births", "maternal_deaths", "low_birth_weight"]) }}
      >
        <LineChart series={outcomes} unit="count" />
      </ChartCard>
    </div>
  );
}
