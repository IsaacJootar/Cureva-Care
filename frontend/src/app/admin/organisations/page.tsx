"use client";

import { useCallback, useEffect, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type {
  AccessLevel,
  FacilityAccessGrant,
  IntelModule,
  Organisation,
  ScopeType,
  SubscriptionTier,
} from "@/lib/types";
import { listTiers } from "@/lib/ops";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Dialog";
import { SelectField, TextField } from "@/components/ui/Field";
import { EmptyState, StatusPill, StatTileSkeleton } from "@/components/ui/Feedback";
import { Table, Td, Th } from "@/components/ui/Table";
import { GeoCascade, type GeoSelection } from "@/components/geo";
import { useToast } from "@/components/ui/Toast";
import { CheckIcon, EditIcon, PlusIcon, ShieldIcon } from "@/components/icons";

// How much personal detail an organisation sees in the records it's granted.
// Short label for the pill; longer plain-language line for the dropdown.
const DETAIL_LABEL: Record<AccessLevel, string> = {
  aggregate: "Totals only",
  de_identified: "No names",
  identifiable: "Full detail",
};
const DETAIL_OPTION: Record<AccessLevel, string> = {
  aggregate: "Totals & charts only — no individual records (default)",
  de_identified: "Individual records, with names & phone numbers removed",
  identifiable: "Full records, including names & contact",
};

interface Paginated<T> {
  count: number;
  results: T[];
}
const asList = <T,>(d: Paginated<T> | T[]): T[] => (Array.isArray(d) ? d : d.results);

// Derive the grant scope from the deepest selected level of the picker.
function scopeFrom(sel: GeoSelection): { scope_type: ScopeType; scope_id: string; label: string } | null {
  if (sel.facilityId) return { scope_type: "facility", scope_id: sel.facilityId, label: sel.labels.facility ?? "facility" };
  if (sel.wardId) return { scope_type: "ward", scope_id: sel.wardId, label: `${sel.labels.ward} (ward)` };
  if (sel.lgaId) return { scope_type: "local_government", scope_id: sel.lgaId, label: `${sel.labels.lga} (LGA)` };
  if (sel.stateId) return { scope_type: "state", scope_id: sel.stateId, label: `${sel.labels.state} (state)` };
  return null;
}

function detailSummary(org: Organisation): string {
  const levels = new Set(org.facility_access.map((g) => DETAIL_LABEL[g.access_level]));
  return levels.size === 0 ? "—" : Array.from(levels).join(", ");
}

export default function OrganisationsPage() {
  const toast = useToast();
  const [orgs, setOrgs] = useState<Organisation[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Organisation | null>(null);

  const load = useCallback(async () => {
    try {
      setOrgs(asList(await apiGet<Paginated<Organisation> | Organisation[]>("/organisations")));
    } catch {
      setOrgs([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AppShell
      title="Organisations"
      subtitle={orgs ? `${orgs.length} organisation${orgs.length === 1 ? "" : "s"}` : "Loading…"}
      allowedRoles={["systems_admin"]}
      action={
        <Button leftIcon={<PlusIcon size={15} />} onClick={() => setCreating(true)}>
          New organisation
        </Button>
      }
    >
      {orgs === null ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
          <StatTileSkeleton />
          <StatTileSkeleton />
          <StatTileSkeleton />
        </div>
      ) : orgs.length === 0 ? (
        <EmptyState
          icon={<ShieldIcon size={24} />}
          heading="No organisations yet"
          hint="Create a customer organisation and grant it view-only access to facilities or whole regions."
          action={
            <Button leftIcon={<PlusIcon size={15} />} onClick={() => setCreating(true)}>
              New organisation
            </Button>
          }
        />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Name</Th>
              <Th>Type</Th>
              <Th>Plan</Th>
              <Th>Facilities / regions granted</Th>
              <Th>Data detail</Th>
              <Th>Active users</Th>
              <Th>Status</Th>
              <Th style={{ textAlign: "right" }}>Actions</Th>
            </tr>
          </thead>
          <tbody>
            {orgs.map((o) => (
              <tr key={o.id}>
                <Td style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{o.name}</Td>
                <Td>{o.org_type ?? "—"}</Td>
                <Td>
                  {o.tier_name ? (
                    <StatusPill status="success">{o.tier_name}</StatusPill>
                  ) : (
                    <span style={{ color: "var(--cv-text-muted)" }}>No plan</span>
                  )}
                  {o.extra_modules && o.extra_modules.length > 0 && (
                    <span style={{ fontSize: 10.5, color: "var(--cv-text-muted)", marginLeft: 6 }}>
                      +{o.extra_modules.length}
                    </span>
                  )}
                </Td>
                <Td>{o.access_summary}</Td>
                <Td>{detailSummary(o)}</Td>
                <Td><span className="cv-num">{o.active_user_count}</span></Td>
                <Td>
                  {o.is_active ? (
                    <StatusPill status="success">Active</StatusPill>
                  ) : (
                    <StatusPill status="neutral">Inactive</StatusPill>
                  )}
                </Td>
                <Td style={{ textAlign: "right" }}>
                  <Button
                    variant="secondary"
                    leftIcon={<EditIcon size={15} />}
                    onClick={() => setEditing(o)}
                    style={{ padding: "6px 12px", fontSize: 12.5 }}
                  >
                    Manage
                  </Button>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {creating && (
        <NewOrganisationModal
          onClose={() => setCreating(false)}
          onCreated={(name) => {
            setCreating(false);
            toast.success(`Organisation “${name}” created.`);
            void load();
          }}
        />
      )}

      {editing && (
        <ManageAccessModal
          org={editing}
          onClose={() => setEditing(null)}
          onChanged={() => {
            void load();
          }}
        />
      )}
    </AppShell>
  );
}

// --- Reusable grant editor (scope picker + tier + add) --------------------
function GrantEditor({ onAdd }: { onAdd: (g: { scope_type: ScopeType; scope_id: string; access_level: AccessLevel; label: string }) => void }) {
  const [sel, setSel] = useState<GeoSelection | null>(null);
  const [tier, setTier] = useState<AccessLevel>("aggregate");
  const scope = sel ? scopeFrom(sel) : null;

  return (
    <div style={{ border: "1px solid var(--cv-card-border)", borderRadius: 10, padding: 14 }}>
      <p style={{ fontSize: 11.5, color: "var(--cv-text-muted)", margin: "0 0 10px" }}>
        Pick one facility, or stop at a state / LGA / ward and leave the facility blank to grant
        every facility in that area (including any added later).
      </p>
      <GeoCascade includeFacility onChange={setSel} />
      <div style={{ display: "flex", gap: 10, alignItems: "flex-end", marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <SelectField id="tier" label="How much detail can they see?" value={tier} onChange={(e) => setTier(e.target.value as AccessLevel)}>
            <option value="aggregate">{DETAIL_OPTION.aggregate}</option>
            <option value="de_identified">{DETAIL_OPTION.de_identified}</option>
            <option value="identifiable">{DETAIL_OPTION.identifiable}</option>
          </SelectField>
        </div>
        <Button
          variant="secondary"
          disabled={!scope}
          onClick={() => {
            if (scope) onAdd({ ...scope, access_level: tier });
          }}
        >
          Add
        </Button>
      </div>
      {scope && (
        <p style={{ fontSize: 11, color: "var(--cv-text-muted)", marginTop: 8 }}>
          Will grant <strong>{scope.label}</strong> — {DETAIL_OPTION[tier].replace(" (default)", "")}.
        </p>
      )}
    </div>
  );
}

function GrantRow({ label, tier, onRemove }: { label: string; tier: AccessLevel; onRemove: () => void }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "8px 11px",
        border: "1px solid var(--cv-card-border)",
        borderRadius: 8,
      }}
    >
      <span style={{ fontSize: 12.5, color: "var(--cv-text-primary)" }}>{label}</span>
      <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
        <StatusPill status="neutral">{DETAIL_LABEL[tier]}</StatusPill>
        <button onClick={onRemove} style={{ background: "none", border: "none", color: "var(--cv-button-danger-bg)", cursor: "pointer", fontSize: 11.5 }}>
          Remove
        </button>
      </span>
    </div>
  );
}

// --- Plan & add-on module editor ------------------------------------------
// A plan (subscription tier) bundles intelligence modules; add-ons unlock extra
// modules on top. These decide which dashboard links a subscriber sees.
function usePlans() {
  const [tiers, setTiers] = useState<SubscriptionTier[]>([]);
  const [modules, setModules] = useState<IntelModule[]>([]);
  useEffect(() => {
    listTiers()
      .then((d) => {
        setTiers([...d.tiers].sort((a, b) => a.order - b.order));
        setModules(d.modules);
      })
      .catch(() => {});
  }, []);
  return { tiers, modules };
}

function PlanEditor({
  tierId,
  extraModules,
  onChange,
}: {
  tierId: string | null;
  extraModules: string[];
  onChange: (next: { tier: string | null; extra_modules: string[] }) => void;
}) {
  const { tiers, modules } = usePlans();
  const selectedTier = tiers.find((t) => t.id === tierId) ?? null;
  const planModules = new Set(selectedTier?.modules ?? []);

  function toggleAddOn(key: string) {
    const next = new Set(extraModules);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    onChange({ tier: tierId, extra_modules: [...next] });
  }

  return (
    <div style={{ border: "1px solid var(--cv-card-border)", borderRadius: 10, padding: 14 }}>
      <SelectField
        id="plan"
        label="Plan"
        value={tierId ?? ""}
        onChange={(e) => onChange({ tier: e.target.value || null, extra_modules: extraModules })}
      >
        <option value="">No plan (no intelligence access)</option>
        {tiers.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name} — {t.modules.length} module{t.modules.length === 1 ? "" : "s"}
          </option>
        ))}
      </SelectField>

      <p style={{ fontSize: 11, color: "var(--cv-text-muted)", margin: "12px 0 8px" }}>
        Add-on modules (unlocked on top of the plan). Modules already in the plan are ticked and locked.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 7 }}>
        {modules.map((m) => {
          const inPlan = planModules.has(m.key);
          const on = inPlan || extraModules.includes(m.key);
          return (
            <button
              key={m.key}
              onClick={() => !inPlan && toggleAddOn(m.key)}
              disabled={inPlan}
              aria-pressed={on}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 10px",
                borderRadius: 7,
                border: `1px solid ${on ? "var(--cv-accent, #6366f1)" : "var(--cv-card-border)"}`,
                background: on ? "var(--cv-accent-soft, rgba(99,102,241,0.08))" : "var(--cv-input-bg)",
                color: "var(--cv-text-primary)",
                cursor: inPlan ? "default" : "pointer",
                opacity: inPlan ? 0.7 : 1,
                textAlign: "left",
                fontSize: 12,
              }}
            >
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 16,
                  height: 16,
                  borderRadius: 4,
                  flexShrink: 0,
                  border: `1.5px solid ${on ? "var(--cv-accent, #6366f1)" : "var(--cv-input-border)"}`,
                  background: on ? "var(--cv-accent, #6366f1)" : "transparent",
                  color: "#fff",
                }}
              >
                {on && <CheckIcon size={11} />}
              </span>
              {m.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// --- New organisation (two-step) ------------------------------------------
interface PendingGrant {
  scope_type: ScopeType;
  scope_id: string;
  access_level: AccessLevel;
  label: string;
}

function NewOrganisationModal({ onClose, onCreated }: { onClose: () => void; onCreated: (name: string) => void }) {
  const [step, setStep] = useState<1 | 2>(1);
  const [name, setName] = useState("");
  const [orgType, setOrgType] = useState("");
  const [tierId, setTierId] = useState<string | null>(null);
  const [extraModules, setExtraModules] = useState<string[]>([]);
  const [grants, setGrants] = useState<PendingGrant[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();

  async function create() {
    setSaving(true);
    setError(undefined);
    try {
      const org = await apiPost<Organisation>("/organisations", {
        name: name.trim(),
        org_type: orgType || null,
        tier: tierId,
        extra_modules: extraModules,
      });
      for (const g of grants) {
        await apiPost(`/organisations/${org.id}/facility-access`, {
          scope_type: g.scope_type,
          scope_id: g.scope_id,
          access_level: g.access_level,
        });
      }
      onCreated(name.trim());
    } catch {
      setError("Could not create the organisation. Please try again.");
      setSaving(false);
    }
  }

  return (
    <Modal open onClose={onClose} width={520}>
      <h2 style={{ fontSize: 16, color: "var(--cv-text-primary)", margin: "0 0 2px" }}>New organisation</h2>
      <p style={{ fontSize: 12, color: "var(--cv-text-muted)", margin: "0 0 18px" }}>Step {step} of 2</p>

      {step === 1 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <TextField id="org-name" label="Organisation name" placeholder="e.g. Kano Maternal Health Trust" value={name} onChange={(e) => setName(e.target.value)} />
          <SelectField id="org-type" label="Type" value={orgType} onChange={(e) => setOrgType(e.target.value)}>
            <option value="">Unspecified</option>
            <option value="NGO">NGO</option>
            <option value="Government">Government</option>
            <option value="Private/business">Private / business</option>
            <option value="Donor">Donor agency</option>
          </SelectField>
          <PlanEditor
            tierId={tierId}
            extraModules={extraModules}
            onChange={({ tier, extra_modules }) => {
              setTierId(tier);
              setExtraModules(extra_modules);
            }}
          />
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8 }}>
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button disabled={name.trim().length === 0} onClick={() => setStep(2)}>Next: access</Button>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <p style={{ fontSize: 12, color: "var(--cv-text-secondary)", margin: 0 }}>
            Choose whose data this organisation can see. They get view-only access to the facilities
            or regions you grant — a region grant covers every facility in it, now and in future.
          </p>
          <GrantEditor onAdd={(g) => setGrants((prev) => [...prev, g])} />

          {grants.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {grants.map((g, i) => (
                <GrantRow key={i} label={g.label} tier={g.access_level} onRemove={() => setGrants((prev) => prev.filter((_, j) => j !== i))} />
              ))}
            </div>
          )}

          {error && <div style={{ color: "var(--cv-danger-text)", fontSize: 11.5 }}>{error}</div>}

          <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
            <Button variant="secondary" onClick={() => setStep(1)}>Back</Button>
            <Button onClick={create} loading={saving} loadingLabel="Creating…">
              Create organisation
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}

// --- Manage access (existing org) -----------------------------------------
function ManageAccessModal({ org, onClose, onChanged }: { org: Organisation; onClose: () => void; onChanged: () => void }) {
  const toast = useToast();
  const [grants, setGrants] = useState<FacilityAccessGrant[]>(org.facility_access);
  const [tierId, setTierId] = useState<string | null>(org.tier);
  const [extraModules, setExtraModules] = useState<string[]>(org.extra_modules ?? []);
  const [savingPlan, setSavingPlan] = useState(false);

  async function savePlan() {
    setSavingPlan(true);
    try {
      await apiPatch(`/organisations/${org.id}`, { tier: tierId, extra_modules: extraModules });
      toast.success("Plan updated.");
      onChanged();
    } catch {
      toast.error("Could not update the plan.");
    } finally {
      setSavingPlan(false);
    }
  }

  async function addGrant(g: PendingGrant) {
    try {
      const created = await apiPost<FacilityAccessGrant>(`/organisations/${org.id}/facility-access`, {
        scope_type: g.scope_type,
        scope_id: g.scope_id,
        access_level: g.access_level,
      });
      setGrants((prev) => [...prev, created]);
      toast.success("Access granted.");
      onChanged();
    } catch {
      toast.error("Could not add the grant.");
    }
  }

  async function revoke(grantId: string) {
    try {
      await apiDelete(`/organisations/${org.id}/facility-access/${grantId}`);
      setGrants((prev) => prev.filter((g) => g.id !== grantId));
      toast.success("Access revoked.");
      onChanged();
    } catch {
      toast.error("Could not revoke the grant.");
    }
  }

  return (
    <Modal open onClose={onClose} width={520}>
      <h2 style={{ fontSize: 16, color: "var(--cv-text-primary)", margin: "0 0 2px" }}>{org.name} — access</h2>
      <p style={{ fontSize: 12, color: "var(--cv-text-muted)", margin: "0 0 18px" }}>
        Choose the plan (which intelligence they can see) and grant view-only facility/region access.
      </p>

      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--cv-text-primary)", marginBottom: 8 }}>Plan & modules</div>
      <PlanEditor
        tierId={tierId}
        extraModules={extraModules}
        onChange={({ tier, extra_modules }) => {
          setTierId(tier);
          setExtraModules(extra_modules);
        }}
      />
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 10, marginBottom: 20 }}>
        <Button onClick={savePlan} loading={savingPlan} style={{ padding: "7px 14px", fontSize: 12 }}>
          Save plan
        </Button>
      </div>

      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--cv-text-primary)", marginBottom: 2 }}>
        Facilities & regions
      </div>
      <p style={{ fontSize: 11.5, color: "var(--cv-text-muted)", margin: "0 0 10px" }}>
        Whose data this organisation can see, and how much personal detail.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
        {grants.length === 0 ? (
          <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No access granted yet.</p>
        ) : (
          grants.map((g) => (
            <GrantRow key={g.id} label={g.scope_label ?? `${g.scope_type}`} tier={g.access_level} onRemove={() => revoke(g.id)} />
          ))
        )}
      </div>

      <GrantEditor onAdd={addGrant} />

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 18 }}>
        <Button variant="secondary" onClick={onClose}>Done</Button>
      </div>
    </Modal>
  );
}
