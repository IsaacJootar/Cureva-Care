"use client";

import { useCallback, useEffect, useState } from "react";
import type { CurrentUser, Role } from "@/lib/types";
import { createUser, deactivateUser, editUser, listUsers, reactivateUser } from "@/lib/ops";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, Modal } from "@/components/ui/Dialog";
import { SelectField, TextField } from "@/components/ui/Field";
import { EmptyState, StatusPill, StatTileSkeleton } from "@/components/ui/Feedback";
import { RowActionsMenu, Table, Td, Th } from "@/components/ui/Table";
import { GeoCascade, type GeoSelection } from "@/components/geo";
import { useToast } from "@/components/ui/Toast";
import { EditIcon, PlusIcon, TrashIcon, UsersIcon } from "@/components/icons";

const ROLE_LABEL: Record<string, string> = {
  systems_admin: "Systems admin",
  facility_lead: "Facility lead",
  data_officer: "Data officer",
  organisation_user: "Organisation user",
};

export default function UsersPage() {
  const toast = useToast();
  const [users, setUsers] = useState<CurrentUser[] | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<CurrentUser | null>(null);
  const [deactivateTarget, setDeactivateTarget] = useState<CurrentUser | null>(null);

  const load = useCallback(() => {
    listUsers().then(setUsers).catch(() => setUsers([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function doDeactivate() {
    if (!deactivateTarget) return;
    try {
      await deactivateUser(deactivateTarget.id);
      toast.success(`${deactivateTarget.name} deactivated.`);
      setDeactivateTarget(null);
      load();
    } catch {
      toast.error("Could not deactivate.");
    }
  }

  return (
    <AppShell
      title="Users & roles"
      subtitle={users ? `${users.length} user${users.length === 1 ? "" : "s"}` : "Loading…"}
      allowedRoles={["systems_admin"]}
      action={<Button leftIcon={<PlusIcon size={15} />} onClick={() => { setEditTarget(null); setFormOpen(true); }}>Create user</Button>}
    >
      {!users ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
          {Array.from({ length: 3 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : users.length === 0 ? (
        <EmptyState icon={<UsersIcon size={24} />} heading="No users yet" />
      ) : (
        <Table>
          <thead><tr><Th>Name</Th><Th>Email</Th><Th>Role</Th><Th>Facility / Org</Th><Th>Status</Th><Th style={{ textAlign: "right" }}>Actions</Th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <Td style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{u.name}</Td>
                <Td>{u.email}</Td>
                <Td>{ROLE_LABEL[u.role]}</Td>
                <Td>{u.facility_name || u.organisation_name || "—"}</Td>
                <Td>{u.is_active ? <StatusPill status="success">Active</StatusPill> : <StatusPill status="neutral">Inactive</StatusPill>}</Td>
                <Td>
                  {u.is_active ? (
                    <RowActionsMenu actions={[
                      { icon: <EditIcon size={16} />, label: "Edit user", onClick: () => { setEditTarget(u); setFormOpen(true); } },
                      { icon: <TrashIcon size={16} />, label: "Deactivate user", destructive: true, onClick: () => setDeactivateTarget(u) },
                    ]} />
                  ) : (
                    <div style={{ textAlign: "right" }}>
                      <Button variant="secondary" onClick={async () => { await reactivateUser(u.id); toast.success("Reactivated."); load(); }}>Reactivate</Button>
                    </div>
                  )}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {formOpen && (
        <UserFormModal
          target={editTarget}
          onClose={() => setFormOpen(false)}
          onSaved={(name) => { setFormOpen(false); toast.success(editTarget ? `${name} updated.` : `${name} created.`); load(); }}
        />
      )}

      <ConfirmDialog
        open={!!deactivateTarget}
        title={`Deactivate ${deactivateTarget?.name}?`}
        consequence="They will immediately lose access. Their past submissions and records are untouched, and you can reactivate them later."
        confirmLabel="Deactivate"
        onCancel={() => setDeactivateTarget(null)}
        onConfirm={doDeactivate}
      />
    </AppShell>
  );
}

function UserFormModal({ target, onClose, onSaved }: { target: CurrentUser | null; onClose: () => void; onSaved: (name: string) => void }) {
  const [name, setName] = useState(target?.name ?? "");
  const [email, setEmail] = useState(target?.email ?? "");
  const [role, setRole] = useState<Role>(target?.role ?? "data_officer");
  const [sel, setSel] = useState<GeoSelection | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();

  const needsFacility = role === "facility_lead";
  const valid = name.trim() && (target || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) && (!needsFacility || target || sel?.facilityId);

  async function save() {
    setSaving(true);
    setError(undefined);
    try {
      if (target) {
        await editUser(target.id, { name: name.trim(), role });
      } else {
        await createUser({ name: name.trim(), email: email.trim(), role, facility: needsFacility ? sel?.facilityId : null });
      }
      onSaved(name.trim());
    } catch {
      setError("Could not save — check the details (email may already be in use).");
      setSaving(false);
    }
  }

  return (
    <Modal open onClose={onClose} width={460}>
      <h2 style={{ fontSize: 16, color: "var(--cv-text-primary)", margin: "0 0 16px" }}>{target ? "Edit user" : "Create user"}</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <TextField id="u-name" label="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <TextField id="u-email" label="Email" type="email" value={email} readOnly={!!target} onChange={(e) => setEmail(e.target.value)} />
        <SelectField id="u-role" label="Role" value={role} onChange={(e) => setRole(e.target.value as Role)}>
          <option value="data_officer">Data officer</option>
          <option value="facility_lead">Facility lead</option>
          <option value="systems_admin">Systems admin</option>
        </SelectField>
        {needsFacility && !target && (
          <div>
            <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--cv-text-secondary)", marginBottom: 6 }}>Assign facility</div>
            <GeoCascade includeFacility onChange={setSel} />
          </div>
        )}
      </div>
      {error && <div style={{ color: "var(--cv-danger-text)", fontSize: 11.5, marginTop: 12 }}>{error}</div>}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={!valid} loading={saving} loadingLabel="Saving…">{target ? "Save changes" : "Create user"}</Button>
      </div>
    </Modal>
  );
}
