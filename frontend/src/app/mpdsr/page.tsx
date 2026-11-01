"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  getMpdsrQueue, getMpdsrSummary, saveMpdsrReview,
  type MpdsrCatalogue, type MpdsrDeath, type MpdsrSummary, type ScopeSel,
} from "@/lib/dashboard";
import { prettyDate } from "@/lib/date";
import { AppShell } from "@/components/layout/AppShell";
import { ChartCard, LeagueTable, type LeagueRow } from "@/components/ui/Charts";
import { StatTile } from "@/components/ui/StatTile";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Dialog";
import { SelectField } from "@/components/ui/Field";
import { ScopeFilter } from "@/components/dashboard/ScopeFilter";
import { useToast } from "@/components/ui/Toast";

export default function MpdsrPage() {
  const { user } = useAuth();
  const isLead = user?.role === "facility_lead";
  const [scope, setScope] = useState<ScopeSel>({});
  const [summary, setSummary] = useState<MpdsrSummary | null>(null);
  const [queue, setQueue] = useState<{ deaths: MpdsrDeath[]; catalogue: MpdsrCatalogue } | null>(null);
  const [editing, setEditing] = useState<MpdsrDeath | null>(null);

  const load = useCallback(() => {
    getMpdsrSummary(scope).then(setSummary).catch(() => setSummary(null));
    if (isLead) getMpdsrQueue().then(setQueue).catch(() => setQueue(null));
  }, [scope, isLead]);
  useEffect(() => { load(); }, [load]);

  const av = (k: string) => summary?.avoidable.find((x) => x.key === k)?.count ?? 0;

  return (
    <AppShell
      title="Death reviews (MPDSR)"
      subtitle="Every maternal and newborn death reviewed: what happened, could it have been prevented, and what's being done"
      allowedRoles={["facility_lead", "organisation_user"]}
      action={!isLead ? <ScopeFilter value={scope} onChange={setScope} /> : undefined}
    >
      {!summary ? (
        <div className="cv-stat-grid"><StatTileSkeleton /><StatTileSkeleton /><StatTileSkeleton /></div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="cv-stat-grid">
            <StatTile status="neutral" label="Deaths to review" value={summary.total_deaths} />
            <StatTile status="success" label="Reviewed" value={summary.reviewed} />
            <StatTile status={summary.awaiting > 0 ? "warning" : "success"} label="Awaiting review" value={summary.awaiting} statusLine={summary.awaiting > 0 ? "not yet looked into" : "all deaths reviewed"} />
            <StatTile status={av("avoidable") + av("probably") > 0 ? "danger" : "neutral"} label="Judged avoidable" value={av("avoidable") + av("probably")} statusLine="deaths that could have been prevented" />
          </div>

          {/* Facility lead: the review queue */}
          {isLead && queue && (
            <ChartCard title="Deaths to review" subtitle="Open each one and record the review — awaiting first">
              {queue.deaths.length === 0 ? (
                <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No deaths recorded in your facility. 🙏</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {queue.deaths.map((d) => (
                    <div key={d.birth_event_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, padding: "10px 12px", border: "1px solid var(--cv-card-border)", borderRadius: 8 }}>
                      <div>
                        <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>{d.woman?.name ?? d.woman?.internal_id ?? "—"}</div>
                        <div style={{ fontSize: 11, color: "var(--cv-danger-text)" }}>{d.outcomes.join(", ")} · {prettyDate(d.delivery_date)}</div>
                      </div>
                      <Button variant={d.reviewed ? "secondary" : "primary"} onClick={() => setEditing(d)} style={{ padding: "6px 12px", fontSize: 12 }}>
                        {d.reviewed ? "Edit review" : "Review"}
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </ChartCard>
          )}

          {summary.reviewed > 0 ? (
            <>
              <ChartCard title="Were these deaths avoidable?" subtitle="A reviewer's judgement, across the deaths reviewed">
                <LeagueTable
                  rows={summary.avoidable.filter((x) => x.count > 0).map((x): LeagueRow => ({ label: x.label, value: x.count, display: `${x.count}` }))}
                  maxRows={6}
                />
              </ChartCard>

              {summary.factors.length > 0 && (
                <ChartCard title="What keeps contributing" subtitle="The problems behind the deaths — tackle the top ones first">
                  <LeagueTable
                    rows={summary.factors.map((x): LeagueRow => ({ label: x.label, value: x.count, display: `${x.count}` }))}
                    maxRows={10}
                  />
                </ChartCard>
              )}

              <ChartCard title="Are the follow-up actions getting done?" subtitle="Status of the actions set during reviews">
                <LeagueTable
                  rows={summary.actions.filter((x) => x.count > 0).map((x): LeagueRow => ({ label: x.label, value: x.count, display: `${x.count}` }))}
                  maxRows={6}
                />
              </ChartCard>
            </>
          ) : (
            <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No reviews completed yet. Once deaths are reviewed, the causes, avoidable factors and follow-up actions appear here.</p>
          )}

          <p style={{ fontSize: 10.5, color: "var(--cv-text-muted)", fontStyle: "italic", margin: 0 }}>
            Whether a death was avoidable is a reviewer’s judgement, recorded by the facility — never decided by the system.
          </p>
        </div>
      )}

      {editing && queue && (
        <ReviewModal death={editing} catalogue={queue.catalogue} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />
      )}
    </AppShell>
  );
}

function ReviewModal({ death, catalogue, onClose, onSaved }: { death: MpdsrDeath; catalogue: MpdsrCatalogue; onClose: () => void; onSaved: () => void }) {
  const toast = useToast();
  const r = death.review;
  const [cause, setCause] = useState(r?.cause ?? "");
  const [avoidable, setAvoidable] = useState(r?.avoidable ?? "unknown");
  const [factors, setFactors] = useState<string[]>(r?.factors ?? []);
  const [action, setAction] = useState(r?.action ?? "");
  const [owner, setOwner] = useState(r?.action_owner ?? "");
  const [status, setStatus] = useState(r?.action_status ?? "open");
  const [saving, setSaving] = useState(false);

  const toggle = (k: string) => setFactors((p) => (p.includes(k) ? p.filter((x) => x !== k) : [...p, k]));

  async function save() {
    setSaving(true);
    try {
      await saveMpdsrReview(death.birth_event_id, { cause, avoidable, factors, action, action_owner: owner, action_status: status });
      toast.success("Review saved.");
      onSaved();
    } catch {
      toast.error("Could not save the review.");
    } finally {
      setSaving(false);
    }
  }

  const inputStyle = { width: "100%", padding: "8px 10px", borderRadius: 7, border: "1px solid var(--cv-input-border)", background: "var(--cv-input-bg)", color: "var(--cv-text-primary)", fontSize: 12.5 } as const;

  return (
    <Modal open onClose={onClose} width={560}>
      <h2 style={{ fontSize: 15, color: "var(--cv-text-primary)", margin: "0 0 2px" }}>Review — {death.woman?.name ?? death.woman?.internal_id}</h2>
      <div style={{ fontSize: 11.5, color: "var(--cv-danger-text)", marginBottom: 14 }}>{death.outcomes.join(", ")} · {prettyDate(death.delivery_date)}</div>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <SelectField id="cause" label="Main cause" value={cause} onChange={(e) => setCause(e.target.value)}>
          <option value="">Not recorded</option>
          {catalogue.causes.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
        </SelectField>

        <SelectField id="avoidable" label="Could it have been prevented?" value={avoidable} onChange={(e) => setAvoidable(e.target.value)}>
          {catalogue.avoidable_options.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
        </SelectField>

        <div>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--cv-text-secondary)", marginBottom: 6 }}>What contributed? (tick any)</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 6 }}>
            {catalogue.factors.map((f) => {
              const on = factors.includes(f.key);
              return (
                <button key={f.key} onClick={() => toggle(f.key)} aria-pressed={on} style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 9px", borderRadius: 7, border: `1px solid ${on ? "var(--cv-accent-solid)" : "var(--cv-card-border)"}`, background: on ? "var(--cv-accent-soft)" : "var(--cv-input-bg)", color: "var(--cv-text-primary)", cursor: "pointer", textAlign: "left", fontSize: 11.5 }}>
                  <span style={{ width: 14, height: 14, borderRadius: 4, flexShrink: 0, border: `1.5px solid ${on ? "var(--cv-accent-solid)" : "var(--cv-input-border)"}`, background: on ? "var(--cv-accent-solid)" : "transparent" }} />
                  {f.label}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--cv-text-secondary)", marginBottom: 6 }}>Follow-up action</div>
          <textarea value={action} onChange={(e) => setAction(e.target.value)} rows={2} placeholder="What should change so this doesn't happen again?" style={inputStyle} />
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <input value={owner} onChange={(e) => setOwner(e.target.value)} placeholder="Who owns it?" style={{ ...inputStyle, flex: 1 }} />
            <div style={{ width: 150 }}>
              <SelectField id="status" label="" value={status} onChange={(e) => setStatus(e.target.value)}>
                {catalogue.action_status_options.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
              </SelectField>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={save} loading={saving} loadingLabel="Saving…">Save review</Button>
        </div>
      </div>
    </Modal>
  );
}
