"use client";

import { useEffect, useState } from "react";
import {
  getCaseTimeline, getClusters, getSevereCases, getSevereTrend,
  type CaseTimeline, type Clusters, type ScopeSel, type SevereCase, type SevereCases, type SevereTrend,
} from "@/lib/dashboard";
import { ScopeFilter } from "@/components/dashboard/ScopeFilter";
import { AppShell } from "@/components/layout/AppShell";
import { Modal } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { StatTile } from "@/components/ui/StatTile";
import { ChartCard, LineChart, LeagueTable, type LineSeries, type LeagueRow } from "@/components/ui/Charts";
import { prettyDate } from "@/lib/date";

const EVENT_LABEL: Record<string, string> = {
  ANC: "Pregnancy check-up",
  Delivery: "Birth",
  PNC: "After-birth check-up",
};

export default function SurveillancePage() {
  const [cases, setCases] = useState<SevereCases | null>(null);
  const [trend, setTrend] = useState<SevereTrend | null>(null);
  const [clusters, setClusters] = useState<Clusters | null>(null);
  const [open, setOpen] = useState<SevereCase | null>(null);
  const [timeline, setTimeline] = useState<CaseTimeline | null>(null);
  const [scope, setScope] = useState<ScopeSel>({});

  useEffect(() => {
    setCases(null); setTrend(null); setClusters(null);
    getSevereCases(scope).then(setCases).catch(() => setCases(null));
    getSevereTrend(scope).then(setTrend).catch(() => setTrend(null));
    getClusters(scope).then(setClusters).catch(() => setClusters(null));
  }, [scope]);

  function openCase(c: SevereCase) {
    setOpen(c);
    setTimeline(null);
    if (c.episode_id) getCaseTimeline(c.episode_id).then(setTimeline).catch(() => setTimeline(null));
  }

  const aggregate = cases?.access_level === "aggregate";
  const trendSeries: LineSeries[] = trend
    ? Object.entries(trend.series).map(([name, pts]) => ({ name, points: pts.map((p) => ({ x: p.x, y: p.value })) }))
    : [];
  const clusterRows: LeagueRow[] = (clusters?.facilities ?? []).map((f) => ({
    label: f.name,
    value: f.severe,
    display: `${f.severe} / ${f.deliveries}${f.rate != null ? ` (${Math.round(f.rate * 100)}%)` : ""}`,
    sublabel: f.region,
  }));

  return (
    <AppShell
      title="Deaths & stillbirths"
      subtitle="Each one, traced back through her record (MPDSR)"
      allowedRoles={["facility_lead", "organisation_user"]}
      action={<ScopeFilter value={scope} onChange={setScope} />}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="cv-stat-grid">
          <StatTile status={cases && cases.count > 0 ? "danger" : "success"} label="Deaths & stillbirths" value={cases?.count ?? 0} />
          <StatTile status="neutral" label="Stillbirths" value={cases?.by_type?.["Stillbirth"] ?? 0} />
          <StatTile status="neutral" label="Newborn deaths (first week)" value={cases?.by_type?.["Newborn death (first 7 days)"] ?? 0} />
          <StatTile status="neutral" label="Mothers who died" value={cases?.by_type?.["Mother died"] ?? 0} />
        </div>

        <ChartCard
          title="Deaths & stillbirths over time"
          subtitle="Stillbirths, newborn deaths & mothers who died, by month"
          note="A rising line is a signal to look closer."
          exportCsv={trend ? {
            name: "deaths-stillbirths-trend",
            header: ["Month", "Stillbirths", "Newborn deaths (first week)", "Mothers who died"],
            rows: trend.buckets.map((b, i) => [b, trend.series["Stillbirth"]?.[i]?.value ?? 0, trend.series["Newborn death (first 7 days)"]?.[i]?.value ?? 0, trend.series["Mother died"]?.[i]?.value ?? 0]),
          } : undefined}
        >
          {!trend || trend.buckets.length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No deaths or stillbirths recorded in this period.</p>
          ) : (
            <LineChart series={trendSeries} unit="count" />
          )}
        </ChartCard>

        <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 16 }}>
          <ChartCard title="Case list" subtitle="Click a case for her full story">
            {aggregate ? (
              <p style={{ fontSize: 11.5, color: "var(--cv-text-muted)" }}>Your access is totals only, so the individual case list isn’t shown.</p>
            ) : !cases || cases.cases.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No cases in this period.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {cases.cases.map((c) => (
                  <button
                    key={c.birth_event_id}
                    onClick={() => openCase(c)}
                    style={{ textAlign: "left", background: "transparent", border: "1px solid var(--cv-card-border)", borderRadius: 8, padding: "10px 12px", cursor: "pointer" }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>{c.woman?.name ?? "(name hidden)"}</span>
                      <span style={{ fontSize: 11, color: "var(--cv-danger-text)", fontWeight: 600 }}>{c.outcomes.join(", ")}</span>
                    </div>
                    <div style={{ fontSize: 11, color: "var(--cv-text-muted)", marginTop: 3 }}>
                      {c.facility} · {prettyDate(c.delivery_date)}
                      {c.antenatal_risk.length > 0 && <> · warning signs during pregnancy: <span style={{ color: "var(--cv-warning-text)" }}>{c.antenatal_risk.join(", ")}</span></>}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </ChartCard>

          <ChartCard
            title="Which facilities to look at"
            subtitle="Highest share of deaths/stillbirths per birth"
            note="Small samples swing easily."
            exportCsv={clusters ? {
              name: "facilities-to-review",
              header: ["Facility", "Region", "Deaths & stillbirths", "Births", "Rate"],
              rows: clusters.facilities.map((f) => [f.name, f.region, f.severe, f.deliveries, f.rate == null ? null : `${Math.round(f.rate * 100)}%`]),
            } : undefined}
          >
            <LeagueTable rows={clusterRows} maxRows={12} />
          </ChartCard>
        </div>
      </div>

      {open && (
        <Modal open onClose={() => setOpen(null)} width={520}>
          <h2 style={{ fontSize: 15, color: "var(--cv-text-primary)", margin: "0 0 4px" }}>{open.woman?.name ?? "Case"}</h2>
          <div style={{ fontSize: 11.5, color: "var(--cv-danger-text)", fontWeight: 600, marginBottom: 2 }}>{open.outcomes.join(", ")}</div>
          <div style={{ fontSize: 11, color: "var(--cv-text-muted)", marginBottom: 14 }}>{open.facility} · {open.region}</div>
          {!open.episode_id ? (
            <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>This case couldn&apos;t be linked to a pregnancy record, so there&apos;s no timeline to show.</p>
          ) : !timeline ? (
            <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>Loading timeline…</p>
          ) : (
            <div style={{ position: "relative", paddingLeft: 16 }}>
              {timeline.events.map((e, i) => (
                <div key={i} style={{ position: "relative", paddingBottom: 14 }}>
                  <span style={{ position: "absolute", left: -16, top: 3, width: 9, height: 9, borderRadius: "50%", background: e.severe && e.severe.length ? "var(--cv-danger-icon)" : "var(--cv-accent-solid)" }} />
                  {i < timeline.events.length - 1 && <span style={{ position: "absolute", left: -12, top: 12, bottom: 0, width: 1, background: "var(--cv-hairline)" }} />}
                  <div style={{ fontSize: 11, color: "var(--cv-text-muted)" }}>{prettyDate(e.date)} · <strong style={{ color: "var(--cv-text-secondary)" }}>{EVENT_LABEL[e.type] ?? e.type}</strong></div>
                  <div style={{ fontSize: 12, color: "var(--cv-text-primary)" }}>{e.summary}</div>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
            <Button variant="secondary" onClick={() => setOpen(null)}>Close</Button>
          </div>
        </Modal>
      )}
    </AppShell>
  );
}
