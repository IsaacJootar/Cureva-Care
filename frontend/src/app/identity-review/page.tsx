"use client";

import { useCallback, useEffect, useState } from "react";
import { confirmCandidate, listCandidates, rejectCandidate, type IdentityCandidate } from "@/lib/identity";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState, StatusPill } from "@/components/ui/Feedback";
import { useToast } from "@/components/ui/Toast";
import { AlertTriangleIcon, CheckIcon, UsersIcon } from "@/components/icons";

export default function IdentityReviewPage() {
  const toast = useToast();
  const [candidates, setCandidates] = useState<IdentityCandidate[] | null>(null);

  const load = useCallback(() => {
    listCandidates().then(setCandidates).catch(() => setCandidates([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function act(id: string, action: "confirm" | "reject") {
    try {
      if (action === "confirm") await confirmCandidate(id);
      else await rejectCandidate(id);
      toast.success(action === "confirm" ? "Match confirmed and linked." : "Match rejected — record stays unlinked.");
      load();
    } catch {
      toast.error("Could not complete the action.");
    }
  }

  return (
    <AppShell
      title="Identity review"
      subtitle={candidates ? `${candidates.length} candidate match${candidates.length === 1 ? "" : "es"} awaiting your confirmation` : "Loading…"}
      allowedRoles={["facility_lead"]}
    >
      {candidates === null ? (
        <p style={{ color: "var(--cv-text-muted)", fontSize: 12.5 }}>Loading…</p>
      ) : candidates.length === 0 ? (
        <EmptyState icon={<UsersIcon size={24} />} heading="No matches to review" hint="Candidate identity matches above the confidence threshold will appear here for confirmation." />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14, maxWidth: 860 }}>
          {candidates.map((c) => (
            <CandidateCard key={c.id} candidate={c} onAct={act} />
          ))}
        </div>
      )}
    </AppShell>
  );
}

function CandidateCard({ candidate, onAct }: { candidate: IdentityCandidate; onAct: (id: string, action: "confirm" | "reject") => void }) {
  const [busy, setBusy] = useState(false);
  const confidencePct = Math.round(parseFloat(candidate.confidence) * 100);
  const values = candidate.new_record.values;
  const keyValues = Object.entries(values).filter(([, v]) => v != null && v !== "").slice(0, 6);

  async function run(action: "confirm" | "reject") {
    setBusy(true);
    await onAct(candidate.id, action);
    setBusy(false);
  }

  return (
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <span style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.4px", color: "var(--cv-text-muted)", fontWeight: 600 }}>
          {candidate.new_record.register_family} record · row {candidate.new_record.row_number}
        </span>
        <StatusPill status={confidencePct >= 85 ? "success" : "warning"}>{confidencePct}% match</StatusPill>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 14, padding: "8px 11px", background: "var(--cv-warning-bg)", border: "1px solid var(--cv-warning-border)", borderRadius: 8 }}>
        <AlertTriangleIcon size={14} />
        <span style={{ fontSize: 11.5, color: "var(--cv-warning-text)" }}>{candidate.reason_label}</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
        {/* New record */}
        <div>
          <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.4px", color: "var(--cv-text-muted)", fontWeight: 600, marginBottom: 8 }}>New record</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {keyValues.map(([k, v]) => (
              <div key={k} style={{ fontSize: 12, color: "var(--cv-text-secondary)" }}>
                <span style={{ color: "var(--cv-text-muted)" }}>{k.replace(/_/g, " ")}: </span>
                <span style={{ color: "var(--cv-text-primary)" }}>{String(v)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Candidate woman */}
        <div>
          <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.4px", color: "var(--cv-text-muted)", fontWeight: 600, marginBottom: 8 }}>Candidate match</div>
          <div style={{ fontSize: 12.5, color: "var(--cv-text-primary)", fontWeight: 600 }}>{candidate.candidate.name || "Unnamed"}</div>
          <div style={{ fontSize: 11, color: "var(--cv-text-muted)" }}>{candidate.candidate.internal_id}</div>
          {candidate.candidate.stable_identifier && (
            <div style={{ fontSize: 11, color: "var(--cv-text-muted)" }}>Card: {candidate.candidate.stable_identifier}</div>
          )}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
            {Object.entries(candidate.matched_fields).map(([k, v]) => (
              <span key={k} style={{ fontSize: 10.5, padding: "2px 8px", borderRadius: "var(--cv-radius-pill)", background: "var(--cv-neutral-pill-bg)", color: "var(--cv-neutral-pill-text)" }}>
                {k.replace(/_/g, " ")}{typeof v === "number" ? ` ${Math.round(v * 100)}%` : ""}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
        <Button variant="secondary" onClick={() => run("reject")} disabled={busy}>Reject</Button>
        <Button leftIcon={<CheckIcon size={15} />} onClick={() => run("confirm")} loading={busy} loadingLabel="Confirming…">Confirm match</Button>
      </div>
    </Card>
  );
}
