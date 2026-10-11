"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { confirmField, getRows, publishIntake, type SourceRow } from "@/lib/intake";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { EmptyState, StatusPill } from "@/components/ui/Feedback";
import { useToast } from "@/components/ui/Toast";
import { AlertTriangleIcon, CheckIcon } from "@/components/icons";

export default function ConfirmFieldsPage() {
  const params = useParams<{ id: string }>();
  const intakeId = params.id;
  const router = useRouter();
  const toast = useToast();
  const [rows, setRows] = useState<SourceRow[] | null>(null);
  const [publishing, setPublishing] = useState(false);

  const load = useCallback(() => {
    getRows(intakeId).then(setRows).catch(() => setRows([]));
  }, [intakeId]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPending = (rows ?? []).reduce((n, r) => n + r.needs_confirmation.length, 0);
  const canPublish = rows !== null && rows.length > 0 && totalPending === 0;

  async function doPublish() {
    setPublishing(true);
    try {
      await publishIntake(intakeId);
      toast.success("Batch published — now visible in intelligence.");
      router.push("/intakes");
    } catch {
      toast.error("Could not publish — some fields still need confirmation.");
      setPublishing(false);
    }
  }

  return (
    <AppShell
      title="Confirm extracted fields"
      subtitle={rows ? `${rows.length} row${rows.length === 1 ? "" : "s"} · ${totalPending} field${totalPending === 1 ? "" : "s"} to confirm` : "Loading…"}
      allowedRoles={["data_officer", "facility_lead"]}
      action={
        <Button onClick={doPublish} disabled={!canPublish} loading={publishing} loadingLabel="Publishing…">
          Publish batch
        </Button>
      }
    >
      {rows === null ? (
        <p style={{ color: "var(--cv-text-muted)", fontSize: 12.5 }}>Loading rows…</p>
      ) : rows.length === 0 ? (
        <EmptyState heading="No rows to confirm" hint="This intake has no extracted rows." />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 820 }}>
          {rows.map((row) => (
            <RowCard key={row.id} intakeId={intakeId} row={row} onChanged={load} />
          ))}
        </div>
      )}
    </AppShell>
  );
}

function RowCard({ intakeId, row, onChanged }: { intakeId: string; row: SourceRow; onChanged: () => void }) {
  const normalized = row.normalized ?? {};
  const fields = Object.keys(normalized);
  const pending = new Set(row.needs_confirmation);

  return (
    <div
      style={{
        background: "var(--cv-card-bg)",
        border: "1px solid var(--cv-card-border)",
        borderRadius: "var(--cv-radius-card)",
        boxShadow: "var(--cv-card-shadow)",
        padding: 18,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: 0 }}>Row {row.row_number}</h3>
        {row.needs_confirmation.length === 0 ? (
          <StatusPill status="success" icon={<CheckIcon size={12} />}>All fields confirmed</StatusPill>
        ) : (
          <StatusPill status="warning" icon={<AlertTriangleIcon size={12} />}>{row.needs_confirmation.length} to confirm</StatusPill>
        )}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))", gap: 10 }}>
        {fields.map((field) => (
          <FieldCell
            key={field}
            intakeId={intakeId}
            rowId={row.id}
            field={field}
            value={normalized[field]}
            confidence={row.extraction_confidence[field]}
            flagged={pending.has(field)}
            flagInfo={row.flags?.[field]}
            onChanged={onChanged}
          />
        ))}
      </div>
    </div>
  );
}

function FieldCell({
  intakeId,
  rowId,
  field,
  value,
  confidence,
  flagged,
  flagInfo,
  onChanged,
}: {
  intakeId: string;
  rowId: string;
  field: string;
  value: unknown;
  confidence?: number;
  flagged: boolean;
  flagInfo?: { kind: string; message: string };
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value ?? ""));
  const [busy, setBusy] = useState(false);

  const label = field.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  async function confirm(correct: boolean) {
    setBusy(true);
    try {
      await confirmField(intakeId, rowId, field, correct, correct ? draft : undefined);
      setEditing(false);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      style={{
        border: `1px solid ${flagged ? "var(--cv-warning-border)" : "var(--cv-hairline)"}`,
        background: flagged ? "var(--cv-warning-bg)" : "transparent",
        borderRadius: 8,
        padding: "9px 11px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.4px", color: "var(--cv-text-muted)", fontWeight: 600 }}>{label}</span>
        {confidence != null && (
          <span className="cv-num" style={{ fontSize: 10, color: flagged ? "var(--cv-warning-text)" : "var(--cv-text-muted)" }}>
            {Math.round(confidence * 100)}%
          </span>
        )}
      </div>
      {editing ? (
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          style={{ width: "100%", marginTop: 5, padding: "5px 7px", borderRadius: 6, border: "1px solid var(--cv-input-border)", background: "var(--cv-input-bg)", color: "var(--cv-text-primary)", fontSize: 12.5 }}
        />
      ) : (
        <div style={{ fontSize: 12.5, color: "var(--cv-text-primary)", marginTop: 3 }}>{String(value ?? "—")}</div>
      )}
      {flagInfo && !editing && (
        <div style={{ fontSize: 10.5, color: "var(--cv-warning-text)", marginTop: 3 }}>{flagInfo.message}</div>
      )}
      {flagged && (
        <div style={{ display: "flex", gap: 6, marginTop: 7 }}>
          {editing ? (
            <>
              <Button variant="secondary" onClick={() => setEditing(false)} style={{ padding: "4px 10px", fontSize: 11 }}>Cancel</Button>
              <Button onClick={() => confirm(true)} loading={busy} style={{ padding: "4px 10px", fontSize: 11 }}>Save correction</Button>
            </>
          ) : (
            <>
              <Button variant="secondary" onClick={() => setEditing(true)} style={{ padding: "4px 10px", fontSize: 11 }}>Correct</Button>
              <Button onClick={() => confirm(false)} loading={busy} style={{ padding: "4px 10px", fontSize: 11 }}>Confirm</Button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
