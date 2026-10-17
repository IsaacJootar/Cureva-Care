"use client";

import { useCallback, useEffect, useState } from "react";
import { downloadRecordsCsv, generateReport, getReport, listReports, type ReportDetail, type ReportSummary, type ReportTypeDef } from "@/lib/reports";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { MetricMeter, LeagueTable, type LeagueRow } from "@/components/ui/Charts";
import { SelectField } from "@/components/ui/Field";
import { EmptyState, StatusPill } from "@/components/ui/Feedback";
import { Toggle } from "@/components/ui/Toggle";
import { useToast } from "@/components/ui/Toast";
import { FileTextIcon, UploadIcon } from "@/components/icons";

type Ratio = { numerator: number; denominator: number; rate: number | null };
const pct = (r: Ratio | undefined | null) => (r && r.rate != null ? `${Math.round(r.rate * 100)}% (${r.numerator}/${r.denominator})` : "no data");

export default function ReportsPage() {
  const toast = useToast();
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [types, setTypes] = useState<ReportTypeDef[]>([]);
  const [reportType, setReportType] = useState("facility_operational");
  const [selected, setSelected] = useState<ReportDetail | null>(null);
  const [withNarrative, setWithNarrative] = useState(false);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(() => {
    listReports().then((d) => { setReports(d.reports); setTypes(d.report_types); }).catch(() => setReports([]));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function generate() {
    setGenerating(true);
    try {
      const report = await generateReport({ report_type: reportType, with_narrative: withNarrative });
      setSelected(report);
      toast.success("Report generated.");
      load();
    } catch {
      toast.error("Could not generate the report.");
    } finally {
      setGenerating(false);
    }
  }

  async function exportCsv() {
    const result = await downloadRecordsCsv();
    if (result === "forbidden") toast.warning("Record export isn't available at your access tier.");
    else if (result === "error") toast.error("Export failed.");
    else toast.success("Records exported.");
  }

  return (
    <AppShell
      title="Reports"
      subtitle="Buyer-ready briefs and dataset exports"
      allowedRoles={["facility_lead", "organisation_user"]}
      action={<Button onClick={generate} loading={generating} loadingLabel="Generating…">Generate report</Button>}
    >
      <div className="cv-reports-grid" style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 18 }}>
        <div className="cv-no-print" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Card padding="14px 16px">
            <div style={{ marginBottom: 12 }}>
              <SelectField id="rtype" label="Report product" value={reportType} onChange={(e) => setReportType(e.target.value)}>
                {types.length === 0 && <option value="facility_operational">Facility operational report</option>}
                {types.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
              </SelectField>
            </div>
            <Toggle checked={withNarrative} onChange={setWithNarrative} label="Include AI narrative" caption="Aggregate-only prose; no identifiable data" />
            <div style={{ marginTop: 12 }}>
              <Button variant="secondary" fullWidth leftIcon={<UploadIcon size={14} />} onClick={exportCsv}>Export records (CSV)</Button>
            </div>
          </Card>
          <div>
            <h2 style={{ fontSize: 12.5, color: "var(--cv-text-muted)", textTransform: "uppercase", letterSpacing: "0.4px", margin: "4px 0 8px" }}>Saved briefs</h2>
            {reports?.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No reports yet.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {reports?.map((r) => (
                  <button key={r.id} onClick={() => getReport(r.id).then(setSelected)}
                    style={{ textAlign: "left", padding: "10px 12px", borderRadius: 8, border: "1px solid var(--cv-card-border)", background: selected?.id === r.id ? "var(--cv-accent-soft)" : "var(--cv-card-bg)", cursor: "pointer" }}>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>{r.title}</div>
                    <div style={{ fontSize: 10.5, color: "var(--cv-text-muted)" }}>{new Date(r.created_at).toLocaleDateString()}{r.has_narrative ? " · narrative" : ""}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="cv-print-area">
          {!selected ? (
            <EmptyState icon={<FileTextIcon size={24} />} heading="No report selected" hint="Pick a product and generate a brief, or open a saved one." />
          ) : (
            <ReportView report={selected} />
          )}
        </div>
      </div>
    </AppShell>
  );
}

function ReportView({ report }: { report: ReportDetail }) {
  const s = report.sections as Record<string, Record<string, unknown>>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 720 }}>
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
          <div>
            <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--cv-text-muted)", fontWeight: 600 }}>Cureva Care · {report.report_type.replace(/_/g, " ")}</div>
            <h2 className="cv-heading" style={{ fontSize: 17, color: "var(--cv-text-primary)", margin: "3px 0 6px" }}>{report.title}</h2>
            <div style={{ fontSize: 11, color: "var(--cv-text-muted)" }}>{report.period_from ?? "all time"} → {report.period_to ?? "now"} · generated {new Date(report.created_at).toLocaleDateString()}</div>
          </div>
          <Button variant="secondary" className="cv-no-print" onClick={() => window.print()}>Print / Save as PDF</Button>
        </div>
        {report.narrative ? (
          <p style={{ fontSize: 12.5, color: "var(--cv-text-secondary)", lineHeight: 1.6, whiteSpace: "pre-wrap", marginTop: 12 }}>{report.narrative}</p>
        ) : (
          <p style={{ fontSize: 11.5, color: "var(--cv-text-muted)", marginTop: 12 }}>Figures reflect recorded register activity, not population rates. Missing fields are not inferred.</p>
        )}
      </Card>

      {report.report_type === "facility_operational" && <FacilityReport s={s} />}
      {report.report_type === "ngo_grant" && <NgoReport s={s} />}
      {report.report_type === "government_surveillance" && <GovReport s={s} />}
    </div>
  );
}

function FacilityReport({ s }: { s: Record<string, Record<string, unknown>> }) {
  const anc = (s.anc_access_continuity ?? {}) as Record<string, Ratio>;
  const sir = (s.screening_intervention_referral ?? {}) as Record<string, Ratio>;
  const outcomes = (s.outcomes ?? {}) as Record<string, number>;
  const actions = (s.ranked_actions as unknown as { action: string; owner: string; rationale: string; measure: string }[]) ?? [];
  return (
    <>
      <Card>
        <h3 className="cv-h3">ANC access & continuity</h3>
        <MetricMeter label="Early ANC booking" ratio={anc.early_booking} />
        <MetricMeter label="4+ ANC contacts" ratio={anc.four_contact} />
        <MetricMeter label="8+ ANC contacts" ratio={anc.eight_contact} />
        <MetricMeter label="Delivery linkage" ratio={anc.delivery_linkage} />
        <MetricMeter label="Postnatal linkage" ratio={anc.postnatal_linkage} />
      </Card>
      <Card>
        <h3 className="cv-h3">Screening, intervention & referral</h3>
        <MetricMeter label="Screening coverage" ratio={sir.screening_coverage} />
        <MetricMeter label="Intervention coverage" ratio={sir.intervention_coverage} />
        <MetricMeter label="Referral closure" ratio={sir.referral_closure} />
      </Card>
      <OutcomesCard outcomes={outcomes} />
      <ActionsCard actions={actions} />
    </>
  );
}

function NgoReport({ s }: { s: Record<string, Record<string, unknown>> }) {
  const cov = (s.coverage_summary ?? {}) as Record<string, Ratio>;
  const equity = (s.equity_by_parity ?? {}) as { bands?: { band: string; contacts: number; screening_coverage: Ratio; intervention_coverage: Ratio }[] };
  const geo = (s.geographic ?? {}) as { areas?: { name: string; rate: number | null; numerator: number; denominator: number | null }[]; label?: string };
  const rdqa = (s.data_quality_rdqa ?? {}) as { mean_score?: number | null; mean_confidence?: number | null; facilities_assessed?: number; total_open_flags?: number };
  const actions = (s.ranked_actions as unknown as { action: string; owner: string; rationale: string; measure: string }[]) ?? [];
  const geoRows: LeagueRow[] = (geo.areas ?? []).map((a) => ({ label: a.name, value: a.rate ?? 0, display: a.rate == null ? "no data" : `${Math.round(a.rate * 100)}% (${a.numerator}/${a.denominator})` }));
  return (
    <>
      <Card>
        <h3 className="cv-h3">Coverage summary</h3>
        <MetricMeter label="Early ANC booking" ratio={cov.early_booking} />
        <MetricMeter label="Screening coverage" ratio={cov.screening_coverage} />
        <MetricMeter label="Intervention coverage" ratio={cov.intervention_coverage} />
      </Card>
      <Card>
        <h3 className="cv-h3">Equity — ANC coverage by parity</h3>
        {(equity.bands ?? []).map((b) => (
          <div key={b.band} style={{ marginBottom: 4 }}>
            <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--cv-text-primary)", marginTop: 6 }}>{b.band} · {b.contacts} contacts</div>
            <MetricMeter label="Screening" ratio={b.screening_coverage} />
          </div>
        ))}
      </Card>
      <Card>
        <h3 className="cv-h3">Geographic — screening coverage by State</h3>
        <LeagueTable rows={geoRows} maxRows={12} />
      </Card>
      <Card>
        <h3 className="cv-h3">Data quality (RDQA)</h3>
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          <Stat label="Mean score" value={rdqa.mean_score ?? "—"} />
          <Stat label="Mean confidence" value={rdqa.mean_confidence != null ? `${Math.round(rdqa.mean_confidence * 100)}%` : "—"} />
          <Stat label="Facilities" value={rdqa.facilities_assessed ?? 0} />
          <Stat label="Open flags" value={rdqa.total_open_flags ?? 0} />
        </div>
      </Card>
      <ActionsCard actions={actions} />
    </>
  );
}

function GovReport({ s }: { s: Record<string, Record<string, unknown>> }) {
  const severe = (s.severe_outcomes ?? {}) as { count?: number; by_type?: Record<string, number> };
  const clusters = (s.facility_clusters ?? {}) as { facilities?: { name: string; severe: number; deliveries: number; rate: number | null }[] };
  const funnel = (s.continuum_funnel ?? {}) as { steps?: { label: string; value: number; share_of_booked: number | null }[] };
  const outcomes = (s.outcomes ?? {}) as Record<string, number>;
  const actions = (s.ranked_actions as unknown as { action: string; owner: string; rationale: string; measure: string }[]) ?? [];
  const clusterRows: LeagueRow[] = (clusters.facilities ?? []).map((f) => ({ label: f.name, value: f.severe, display: `${f.severe} / ${f.deliveries}${f.rate != null ? ` (${Math.round(f.rate * 100)}%)` : ""}` }));
  return (
    <>
      <Card>
        <h3 className="cv-h3">Severe-outcome surveillance (MPDSR)</h3>
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          <Stat label="Severe outcomes" value={severe.count ?? 0} />
          <Stat label="Stillbirths" value={severe.by_type?.["Stillbirth"] ?? 0} />
          <Stat label="Early neonatal deaths" value={severe.by_type?.["Early neonatal death"] ?? 0} />
          <Stat label="Maternal deaths" value={severe.by_type?.["Maternal death"] ?? 0} />
        </div>
      </Card>
      <Card>
        <h3 className="cv-h3">Facility clustering</h3>
        <LeagueTable rows={clusterRows} maxRows={12} />
      </Card>
      <Card>
        <h3 className="cv-h3">Care-journey continuum</h3>
        {(funnel.steps ?? []).map((st) => (
          <MetricMeter key={st.label} label={st.label} ratio={{ numerator: st.value, denominator: funnel.steps?.[0]?.value ?? st.value, rate: st.share_of_booked }} />
        ))}
      </Card>
      <OutcomesCard outcomes={outcomes} />
      <ActionsCard actions={actions} />
    </>
  );
}

function OutcomesCard({ outcomes }: { outcomes: Record<string, number> }) {
  return (
    <Card>
      <h3 className="cv-h3">Documented outcomes</h3>
      <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
        {["live_births", "still_births", "maternal_deaths", "low_birth_weight"].map((k) => (
          <Stat key={k} label={k.replace(/_/g, " ")} value={outcomes[k] ?? 0} />
        ))}
      </div>
    </Card>
  );
}

function ActionsCard({ actions }: { actions: { action: string; owner: string; rationale: string; measure: string }[] }) {
  if (!actions.length) return null;
  return (
    <Card>
      <h3 className="cv-h3">Ranked actions</h3>
      {actions.map((a, i) => (
        <div key={i} style={{ padding: "10px 0", borderBottom: "1px solid var(--cv-hairline)" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>{i + 1}. {a.action}</span>
            <StatusPill status="neutral">{a.owner}</StatusPill>
          </div>
          <div style={{ fontSize: 11, color: "var(--cv-text-muted)", marginTop: 3 }}>{a.rationale} · measure: {a.measure}</div>
        </div>
      ))}
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div style={{ fontSize: 10.5, textTransform: "uppercase", color: "var(--cv-text-muted)", fontWeight: 600 }}>{label}</div>
      <div className="cv-num" style={{ fontSize: 20, fontWeight: 700, color: "var(--cv-text-primary)" }}>{String(value)}</div>
    </div>
  );
}
