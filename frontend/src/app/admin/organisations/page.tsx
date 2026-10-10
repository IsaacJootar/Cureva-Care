"use client";

import { useCallback, useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import type { AccessLevel, FacilityAccessGrant, Organisation, ScopeType } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Dialog";
import { SelectField, TextField } from "@/components/ui/Field";
import { EmptyState, StatusPill, StatTileSkeleton } from "@/components/ui/Feedback";
import { RowActionsMenu, Table, Td, Th } from "@/components/ui/Table";
import { GeoCascade, type GeoSelection } from "@/components/geo";
import { useToast } from "@/components/ui/Toast";
import { EditIcon, PlusIcon, ShieldIcon } from "@/components/icons";

const TIER_LABEL: Record<AccessLevel, string> = {
  aggregate: "Aggregate",
  de_identified: "De-identified",
  identifiable: "Identifiable",
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

function tierSummary(org: Organisation): string {
  const tiers = new Set(org.facility_access.map((g) => TIER_LABEL[g.access_level]));
  return tiers.size === 0 ? "—" : Array.from(tiers).join(", ");
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
              <Th>Facilities / regions granted</Th>
              <Th>Access tier</Th>
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
                <Td>{o.access_summary}</Td>
                <Td>{tierSummary(o)}</Td>
                <Td><span className="cv-num">{o.active_user_count}</span></Td>
                <Td>
                  {o.is_active ? (
                    <StatusPill status="success">Active</StatusPill>
                  ) : (
                    <StatusPill status="neutral">Inactive</StatusPill>
                  )}
                </Td>
                <Td>
                  <RowActionsMenu
                    actions={[
                      {
                        icon: <EditIcon size={16} />,
                        label: "Manage access",
                        onClick: () => setEditing(o),
                      },
                    ]}
                  />
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
      <GeoCascade includeFacility onChange={setSel} />
      <div style={{ display: "flex", gap: 10, alignItems: "flex-end", marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <SelectField id="tier" label="Access tier" value={tier} onChange={(e) => setTier(e.target.value as AccessLevel)}>
            <option value="aggregate">Aggregate (least identifiable — default)</option>
            <option value="de_identified">De-identified</option>
            <option value="identifiable">Identifiable</option>
          </SelectField>
        </div>
        <Button
          variant="secondary"
          disabled={!scope}
          onClick={() => {
            if (scope) onAdd({ ...scope, access_level: tier });
          }}
        >
          Add grant
        </Button>
      </div>
      {scope && (
        <p style={{ fontSize: 11, color: "var(--cv-text-muted)", marginTop: 8 }}>
          Will grant: <strong>{scope.label}</strong> at {TIER_LABEL[tier]} tier.
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
        <StatusPill status="neutral">{TIER_LABEL[tier]}</StatusPill>
        <button onClick={onRemove} style={{ background: "none", border: "none", color: "var(--cv-button-danger-bg)", cursor: "pointer", fontSize: 11.5 }}>
          Remove
        </button>
      </span>
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
  const [grants, setGrants] = useState<PendingGrant[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();

  async function create() {
    setSaving(true);
    setError(undefined);
    try {
      const org = await apiPost<Organisation>("/organisations", { name: name.trim(), org_type: orgType || null });
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
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8 }}>
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button disabled={name.trim().length === 0} onClick={() => setStep(2)}>Next: access</Button>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <p style={{ fontSize: 12, color: "var(--cv-text-secondary)", margin: 0 }}>
            Grant view-only access to facilities or whole regions. A region grant auto-expands to every facility under it, present and future. New organisations default to the Aggregate tier.
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
        Grant or revoke this organisation&apos;s view-only facility/region access.
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
