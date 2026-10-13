"use client";

import { useCallback, useEffect, useState } from "react";
import { downloadRecordsCsv, generateReport, getReport, listReports, type ReportDetail, type ReportSummary } from "@/lib/reports";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { MetricMeter } from "@/components/ui/Charts";
import { EmptyState, StatusPill } from "@/components/ui/Feedback";
import { Toggle } from "@/components/ui/Toggle";
import { useToast } from "@/components/ui/Toast";
import { FileTextIcon, UploadIcon } from "@/components/icons";

type Ratio = { numerator: number; denominator: number; rate: number | null };

export default function ReportsPage() {
  const toast = useToast();
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [selected, setSelected] = useState<ReportDetail | null>(null);
  const [withNarrative, setWithNarrative] = useState(false);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(() => {
    listReports().then(setReports).catch(() => setReports([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function generate() {
    setGenerating(true);
    try {
      const report = await generateReport({ with_narrative: withNarrative });
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
      subtitle="Analytical briefs and dataset exports"
      allowedRoles={["facility_lead", "organisation_user"]}
      action={<Button onClick={generate} loading={generating} loadingLabel="Generating…">Generate report</Button>}
    >
      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 18 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Card padding="14px 16px">
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
                  <button
                    key={r.id}
                    onClick={() => getReport(r.id).then(setSelected)}
                    style={{ textAlign: "left", padding: "10px 12px", borderRadius: 8, border: "1px solid var(--cv-card-border)", background: selected?.id === r.id ? "var(--cv-accent-soft)" : "var(--cv-card-bg)", cursor: "pointer" }}
                  >
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>{r.title}</div>
                    <div style={{ fontSize: 10.5, color: "var(--cv-text-muted)" }}>{new Date(r.created_at).toLocaleString()}{r.has_narrative ? " · narrative" : ""}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div>
          {!selected ? (
            <EmptyState icon={<FileTextIcon size={24} />} heading="No report selected" hint="Generate a brief or pick a saved one to view it." />
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
  const anc = s.anc_access_continuity as Record<string, Ratio | number>;
  const sir = s.screening_intervention_referral as Record<string, Ratio>;
  const outcomes = s.outcomes as Record<string, number | Record<string, unknown>>;
  const actions = (s.ranked_actions as unknown as { action: string; owner: string; rationale: string; measure: string }[]) ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 680 }}>
      <Card>
        <h2 className="cv-heading" style={{ fontSize: 16, color: "var(--cv-text-primary)", margin: "0 0 8px" }}>{report.title}</h2>
        {report.narrative ? (
          <p style={{ fontSize: 12.5, color: "var(--cv-text-secondary)", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{report.narrative}</p>
        ) : (
          <p style={{ fontSize: 11.5, color: "var(--cv-text-muted)" }}>Deterministic brief (no AI narrative). Figures reflect recorded register activity, not population rates.</p>
        )}
      </Card>

      <Card>
        <h3 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: "0 0 10px" }}>ANC access & continuity</h3>
        <MetricMeter label="Early ANC booking" ratio={anc.early_booking as Ratio} />
        <MetricMeter label="4+ ANC contacts" ratio={anc.four_contact as Ratio} />
        <MetricMeter label="8+ ANC contacts" ratio={anc.eight_contact as Ratio} />
        <MetricMeter label="Delivery linkage" ratio={anc.delivery_linkage as Ratio} />
        <MetricMeter label="Postnatal linkage" ratio={anc.postnatal_linkage as Ratio} />
      </Card>

      <Card>
        <h3 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: "0 0 10px" }}>Screening, intervention & referral</h3>
        <MetricMeter label="Screening coverage" ratio={sir.screening_coverage} />
        <MetricMeter label="Intervention coverage" ratio={sir.intervention_coverage} />
        <MetricMeter label="Referral closure" ratio={sir.referral_closure} />
      </Card>

      <Card>
        <h3 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: "0 0 10px" }}>Documented outcomes</h3>
        <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
          {["live_births", "still_births", "maternal_deaths", "low_birth_weight"].map((k) => (
            <div key={k}>
              <div style={{ fontSize: 10.5, textTransform: "uppercase", color: "var(--cv-text-muted)", fontWeight: 600 }}>{k.replace(/_/g, " ")}</div>
              <div className="cv-num" style={{ fontSize: 20, fontWeight: 700, color: "var(--cv-text-primary)" }}>{String(outcomes[k])}</div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h3 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: "0 0 10px" }}>Three ranked actions</h3>
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
    </div>
  );
}
