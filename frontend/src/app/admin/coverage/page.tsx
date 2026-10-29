"use client";

import { useCallback, useEffect, useState } from "react";
import { listCoverageDenominators, saveCoverageDenominator, type CoverageDenominatorRow } from "@/lib/ops";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SelectField } from "@/components/ui/Field";
import { EmptyState, StatTileSkeleton } from "@/components/ui/Feedback";
import { useToast } from "@/components/ui/Toast";
import { TargetIcon } from "@/components/icons";

const YEARS = [2027, 2026, 2025, 2024];

export default function CoverageAdminPage() {
  const [year, setYear] = useState(2026);
  const [rows, setRows] = useState<CoverageDenominatorRow[] | null>(null);

  const load = useCallback(() => {
    setRows(null);
    listCoverageDenominators(year).then((d) => setRows(d.rows)).catch(() => setRows([]));
  }, [year]);
  useEffect(() => { load(); }, [load]);

  return (
    <AppShell
      title="Population estimates"
      subtitle="Load the expected pregnancies and births per LGA so the Coverage page can show reach. These are estimates (e.g. WorldPop, national projections)."
      allowedRoles={["systems_admin"]}
      action={
        <div style={{ width: 120 }}>
          <SelectField id="year" label="" value={String(year)} onChange={(e) => setYear(Number(e.target.value))}>
            {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
          </SelectField>
        </div>
      }
    >
      {!rows ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 820, margin: "0 auto" }}>
          {Array.from({ length: 3 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : rows.length === 0 ? (
        <EmptyState icon={<TargetIcon size={24} />} heading="No LGAs with facilities yet" hint="Once facilities exist, their LGAs appear here to load population estimates against." />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 820, margin: "0 auto" }}>
          <p style={{ fontSize: 11.5, color: "var(--cv-text-muted)", margin: "0 0 2px" }}>
            Expected number of pregnant women (and, optionally, births) in each LGA for {year}. Leave a field blank to show no coverage for that area until you have an estimate.
          </p>
          {rows.map((r) => <DenominatorRow key={r.area_id} row={r} year={year} />)}
        </div>
      )}
    </AppShell>
  );
}

function DenominatorRow({ row, year }: { row: CoverageDenominatorRow; year: number }) {
  const toast = useToast();
  const [preg, setPreg] = useState(row.expected_pregnancies?.toString() ?? "");
  const [births, setBirths] = useState(row.expected_births?.toString() ?? "");
  const [source, setSource] = useState(row.source ?? "");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await saveCoverageDenominator({
        area_id: row.area_id,
        year,
        expected_pregnancies: preg === "" ? null : Math.max(0, Math.round(Number(preg))),
        expected_births: births === "" ? null : Math.max(0, Math.round(Number(births))),
        source: source.trim(),
      });
      toast.success(`${row.name} estimate saved.`);
    } catch {
      toast.error("Could not save that estimate.");
    } finally {
      setSaving(false);
    }
  }

  const inputStyle = { width: "100%", padding: "7px 9px", borderRadius: 7, border: "1px solid var(--cv-input-border)", background: "var(--cv-input-bg)", color: "var(--cv-text-primary)", fontSize: 12.5 } as const;

  return (
    <Card padding="12px 14px">
      <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 160px", minWidth: 140 }}>
          <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>{row.name}</div>
          <div style={{ fontSize: 10.5, color: "var(--cv-text-muted)" }}>{row.state_name}</div>
        </div>
        <label style={{ flex: "0 0 120px" }}>
          <div style={{ fontSize: 10.5, color: "var(--cv-text-muted)", marginBottom: 3 }}>Expected pregnancies</div>
          <input type="number" min={0} inputMode="numeric" value={preg} onChange={(e) => setPreg(e.target.value)} style={inputStyle} />
        </label>
        <label style={{ flex: "0 0 110px" }}>
          <div style={{ fontSize: 10.5, color: "var(--cv-text-muted)", marginBottom: 3 }}>Expected births</div>
          <input type="number" min={0} inputMode="numeric" value={births} onChange={(e) => setBirths(e.target.value)} style={inputStyle} />
        </label>
        <label style={{ flex: "1 1 150px", minWidth: 120 }}>
          <div style={{ fontSize: 10.5, color: "var(--cv-text-muted)", marginBottom: 3 }}>Source</div>
          <input type="text" placeholder="e.g. WorldPop 2026" value={source} onChange={(e) => setSource(e.target.value)} style={inputStyle} />
        </label>
        <Button onClick={save} loading={saving} style={{ padding: "8px 14px", fontSize: 12 }}>Save</Button>
      </div>
    </Card>
  );
}
