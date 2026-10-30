"use client";

import { useCallback, useEffect, useState } from "react";
import { actionItem, getWorklist, type WorklistItem } from "@/lib/worklist";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { EmptyState, StatusPill, StatTileSkeleton, type Status } from "@/components/ui/Feedback";
import { Table, Td, Th } from "@/components/ui/Table";
import { useToast } from "@/components/ui/Toast";
import { CheckIcon } from "@/components/icons";

const SEVERITY: Record<string, Status> = { high: "danger", medium: "warning", low: "neutral" };

export default function NeedsAttentionPage() {
  const toast = useToast();
  const [items, setItems] = useState<WorklistItem[] | null>(null);

  const load = useCallback(() => {
    getWorklist().then((d) => setItems(d.items)).catch(() => setItems([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <AppShell
      title="Needs attention"
      subtitle={items ? `${items.length} item${items.length === 1 ? "" : "s"} to follow up` : "Loading…"}
      allowedRoles={["facility_lead"]}
    >
      {!items ? (
        <div className="cv-stat-grid">
          {Array.from({ length: 3 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : items.length === 0 ? (
        <EmptyState icon={<CheckIcon size={24} />} heading="Nothing needs attention" hint="No risks, referrals, or follow-ups are flagged for your facility right now." />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Woman / record</Th>
              <Th>Reason</Th>
              <Th>Severity</Th>
              <Th>Days open</Th>
              <Th style={{ textAlign: "right" }}>Follow-up</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <WorklistRow key={item.item_id} item={item} onActioned={() => { toast.success("Follow-up recorded."); load(); }} />
            ))}
          </tbody>
        </Table>
      )}
    </AppShell>
  );
}

function WorklistRow({ item, onActioned }: { item: WorklistItem; onActioned: () => void }) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    try {
      await actionItem(item.item_id, note, item.subject_type);
      setOpen(false);
      setNote("");
      onActioned();
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr>
      <Td style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>
        {item.woman?.name || item.woman?.internal_id || item.subject_type}
        {item.woman?.name && <span style={{ fontWeight: 400, color: "var(--cv-text-muted)", fontSize: 11 }}> · {item.woman.internal_id}</span>}
      </Td>
      <Td>
        {item.label}
        <div style={{ fontSize: 11, color: "var(--cv-text-muted)" }}>{item.reason}</div>
        {item.last_actioned && (
          <div style={{ fontSize: 10.5, color: "var(--cv-text-muted)", marginTop: 3 }}>
            Actioned {new Date(item.last_actioned.at).toLocaleDateString()} by {item.last_actioned.by}
            {item.last_actioned.note ? ` — “${item.last_actioned.note}”` : ""}
          </div>
        )}
        {open && (
          <div style={{ display: "flex", gap: 8, marginTop: 8, maxWidth: 420 }}>
            <div style={{ flex: 1 }}>
              <TextField id={`note-${item.item_id}`} placeholder="What did you do? (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
            </div>
            <Button onClick={submit} loading={busy} loadingLabel="Saving…" style={{ alignSelf: "stretch" }}>Confirm</Button>
          </div>
        )}
      </Td>
      <Td><StatusPill status={SEVERITY[item.severity]}>{item.severity}</StatusPill></Td>
      <Td><span className="cv-num">{item.days_open ?? "—"}</span></Td>
      <Td style={{ textAlign: "right" }}>
        {!open && <Button variant="secondary" onClick={() => setOpen(true)}>Mark actioned</Button>}
      </Td>
    </tr>
  );
}
