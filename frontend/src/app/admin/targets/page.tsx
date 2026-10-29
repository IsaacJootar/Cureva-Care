"use client";

import { useEffect, useState } from "react";
import { listTargets, updateTarget, type ProgramTargetRow } from "@/lib/ops";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { Toggle } from "@/components/ui/Toggle";
import { useToast } from "@/components/ui/Toast";

export default function TargetsAdminPage() {
  const [rows, setRows] = useState<ProgramTargetRow[] | null>(null);

  useEffect(() => {
    listTargets().then((d) => setRows(d.targets)).catch(() => setRows([]));
  }, []);

  return (
    <AppShell
      title="Goals & targets"
      subtitle="Set the target percentage for each goal (e.g. SDG / national coverage targets). Subscribers see progress against these."
      allowedRoles={["systems_admin"]}
    >
      {!rows ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 700, margin: "0 auto" }}>
          {Array.from({ length: 4 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 700, margin: "0 auto" }}>
          {rows.map((r) => <TargetRow key={r.key} row={r} />)}
        </div>
      )}
    </AppShell>
  );
}

function TargetRow({ row }: { row: ProgramTargetRow }) {
  const toast = useToast();
  const [pct, setPct] = useState(String(row.target_pct));
  const [active, setActive] = useState(row.is_active);
  const [saving, setSaving] = useState(false);

  async function save(next: { target_pct?: number; is_active?: boolean }) {
    setSaving(true);
    try {
      await updateTarget(row.key, next);
      toast.success(`${row.label} updated.`);
    } catch {
      toast.error("Could not save that target.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card padding="13px 15px">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
        <div style={{ flex: 1, opacity: active ? 1 : 0.55 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--cv-text-primary)" }}>{row.label}</div>
          <div style={{ fontSize: 11.5, color: "var(--cv-text-muted)", marginTop: 3 }}>{row.help}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <input
              type="number" min={0} max={100} inputMode="numeric"
              value={pct} onChange={(e) => setPct(e.target.value)}
              disabled={!active}
              style={{ width: 64, padding: "7px 9px", borderRadius: 7, border: "1px solid var(--cv-input-border)", background: "var(--cv-input-bg)", color: "var(--cv-text-primary)", fontSize: 13, textAlign: "center" }}
            />
            <span style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>%</span>
          </div>
          <Button onClick={() => save({ target_pct: Math.max(0, Math.min(100, Number(pct) || 0)) })} loading={saving} disabled={!active} style={{ padding: "7px 12px", fontSize: 12 }}>Save</Button>
          <Toggle checked={active} onChange={(v) => { setActive(v); save({ is_active: v }); }} ariaLabel={`${row.label} active`} />
        </div>
      </div>
    </Card>
  );
}
