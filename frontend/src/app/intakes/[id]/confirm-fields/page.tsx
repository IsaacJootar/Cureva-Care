"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { confirmField, getPages, getRows, publishIntake, type IntakePage, type SourceRow } from "@/lib/intake";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { EmptyState, StatusPill } from "@/components/ui/Feedback";
import { useToast } from "@/components/ui/Toast";
import { AlertTriangleIcon, CheckIcon, ChevronLeftIcon } from "@/components/icons";

export default function ConfirmFieldsPage() {
  const params = useParams<{ id: string }>();
  const intakeId = params.id;
  const router = useRouter();
  const toast = useToast();
  const [rows, setRows] = useState<SourceRow[] | null>(null);
  const [pages, setPages] = useState<IntakePage[]>([]);
  const [publishing, setPublishing] = useState(false);

  const load = useCallback(() => {
    getRows(intakeId).then(setRows).catch(() => setRows([]));
    getPages(intakeId).then(setPages).catch(() => setPages([]));
  }, [intakeId]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPending = (rows ?? []).reduce((n, r) => n + r.needs_confirmation.length, 0);
  const canPublish = rows !== null && rows.length > 0 && totalPending === 0;

  // Columns the AI read off the page but that don't match this register's
  // template. They are NOT part of the per-row confirmation (there is no
  // canonical field to confirm them against), so they never appear as "to
  // confirm" — but the officer should still know they weren't captured.
  const unmatched = Array.from(new Set((rows ?? []).flatMap((r) => r.unmatched_labels ?? []))).sort();
  const sampleValue = (label: string): string | null => {
    for (const r of rows ?? []) {
      const v = (r.raw_payload as Record<string, unknown> | null)?.[label];
      if (v !== undefined && v !== null && String(v).trim() !== "") return String(v);
    }
    return null;
  };

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
      <button
        onClick={() => router.push("/intakes")}
        style={{
          display: "inline-flex", alignItems: "center", gap: 4,
          background: "none", border: "none", cursor: "pointer",
          color: "var(--cv-text-secondary)", fontSize: 12.5, padding: 0, marginBottom: 14,
        }}
      >
        <ChevronLeftIcon size={15} /> Back to intakes
      </button>

      {unmatched.length > 0 && (
        <div style={{ background: "var(--cv-warning-bg)", border: "1px solid var(--cv-warning-border)", borderRadius: "var(--cv-radius-card)", padding: 14, marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 9, alignItems: "flex-start" }}>
            <span style={{ color: "var(--cv-warning-icon)", flexShrink: 0 }}><AlertTriangleIcon size={17} /></span>
            <div>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)", marginBottom: 4 }}>
                {unmatched.length} column{unmatched.length === 1 ? "" : "s"} couldn&apos;t be matched to this register&apos;s template
              </div>
              <p style={{ fontSize: 11.5, color: "var(--cv-text-secondary)", margin: "0 0 8px" }}>
                These were read from the page but aren&apos;t known fields, so they <strong>won&apos;t be saved</strong> for this
                batch. The matched fields below are unaffected. Ask a systems admin to map these so future imports capture them.
              </p>
              <ul style={{ margin: 0, paddingLeft: 16, fontSize: 11.5, color: "var(--cv-text-primary)" }}>
                {unmatched.map((label) => {
                  const s = sampleValue(label);
                  return <li key={label}><strong>{label}</strong>{s ? ` — e.g. “${s}”` : ""}</li>;
                })}
              </ul>
            </div>
          </div>
        </div>
      )}

      {rows === null ? (
        <p style={{ color: "var(--cv-text-muted)", fontSize: 12.5 }}>Loading rows…</p>
      ) : rows.length === 0 ? (
        <EmptyState heading="No rows to confirm" hint="This intake has no extracted rows." />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {pages.some((p) => p.url) && (
            <div style={{ background: "var(--cv-card-bg)", border: "1px solid var(--cv-card-border)", borderRadius: "var(--cv-radius-card)", padding: 14 }}>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.4px", color: "var(--cv-text-muted)", fontWeight: 600, marginBottom: 8 }}>
                Register photo — check identity fields against it
              </div>
              <div style={{ display: "flex", gap: 10, overflowX: "auto" }}>
                {pages.filter((p) => p.url).map((p) => (
                  <a key={p.page_number} href={p.url!} target="_blank" rel="noreferrer" title={`Open page ${p.page_number}`}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={p.url!} alt={`Register page ${p.page_number}`} style={{ height: 150, borderRadius: 8, border: "1px solid var(--cv-card-border)" }} />
                  </a>
                ))}
              </div>
            </div>
          )}
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
            isIdentity={(row.always_confirm ?? []).includes(field)}
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
  isIdentity,
  flagInfo,
  onChanged,
}: {
  intakeId: string;
  rowId: string;
  field: string;
  value: unknown;
  confidence?: number;
  flagged: boolean;
  isIdentity?: boolean;
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
        <span style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.4px", color: "var(--cv-text-muted)", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 6 }}>
          {label}
          {isIdentity && (
            <span style={{ fontSize: 8.5, padding: "1px 5px", borderRadius: 10, background: "var(--cv-neutral-pill-bg)", color: "var(--cv-neutral-pill-text)", letterSpacing: "0.2px" }}>IDENTITY</span>
          )}
        </span>
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
