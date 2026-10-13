"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { CurrentUser } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Dialog";
import { TextField } from "@/components/ui/Field";
import { EmptyState, StatusPill, StatTileSkeleton } from "@/components/ui/Feedback";
import { Table, Td, Th } from "@/components/ui/Table";
import { Toggle } from "@/components/ui/Toggle";
import { useToast } from "@/components/ui/Toast";
import { PlusIcon, UsersIcon } from "@/components/icons";

export default function OrgUsersPage() {
  const { user } = useAuth();
  const toast = useToast();
  const orgId = user?.organisation;
  const [users, setUsers] = useState<CurrentUser[] | null>(null);
  const [inviting, setInviting] = useState(false);

  const load = useCallback(() => {
    if (!orgId) return;
    apiGet<CurrentUser[]>(`/organisations/${orgId}/users`).then(setUsers).catch(() => setUsers([]));
  }, [orgId]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <AppShell
      title="My organisation's users"
      subtitle={users ? `${users.length} user${users.length === 1 ? "" : "s"}` : "Loading…"}
      allowedRoles={["organisation_user"]}
      action={<Button leftIcon={<PlusIcon size={15} />} onClick={() => setInviting(true)}>Invite user</Button>}
    >
      {!users ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
          {Array.from({ length: 3 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : users.length === 0 ? (
        <EmptyState icon={<UsersIcon size={24} />} heading="No users yet" hint="Invite colleagues into your organisation." />
      ) : (
        <Table>
          <thead><tr><Th>Name</Th><Th>Email</Th><Th>Role</Th><Th>Manages users</Th><Th>Status</Th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <Td style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{u.name}</Td>
                <Td>{u.email}</Td>
                <Td>Organisation user</Td>
                <Td>{u.can_manage_org_users ? "Yes" : "—"}</Td>
                <Td><StatusPill status="success">Active</StatusPill></Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {inviting && orgId && (
        <InviteModal
          orgId={orgId}
          onClose={() => setInviting(false)}
          onInvited={(name) => {
            setInviting(false);
            toast.success(`Invited ${name}.`);
            load();
          }}
        />
      )}
    </AppShell>
  );
}

function InviteModal({ orgId, onClose, onInvited }: { orgId: string; onClose: () => void; onInvited: (name: string) => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [canManage, setCanManage] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  async function invite() {
    setBusy(true);
    setError(undefined);
    try {
      await apiPost(`/organisations/${orgId}/users`, { name: name.trim(), email: email.trim(), can_manage_org_users: canManage });
      onInvited(name.trim());
    } catch {
      setError("Could not invite — check the email isn't already in use.");
      setBusy(false);
    }
  }

  const valid = name.trim() && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

  return (
    <Modal open onClose={onClose} width={420}>
      <h2 style={{ fontSize: 16, color: "var(--cv-text-primary)", margin: "0 0 4px" }}>Invite user</h2>
      <p style={{ fontSize: 12, color: "var(--cv-text-muted)", margin: "0 0 18px" }}>
        Every invited user joins as an Organisation user, scoped to your organisation's granted facilities.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <TextField id="inv-name" label="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <TextField id="inv-email" label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Toggle checked={canManage} onChange={setCanManage} label="Can manage organisation users" caption="Lets them invite and manage colleagues too" />
      </div>
      {error && <div style={{ color: "var(--cv-danger-text)", fontSize: 11.5, marginTop: 12 }}>{error}</div>}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button onClick={invite} disabled={!valid} loading={busy} loadingLabel="Inviting…">Send invite</Button>
      </div>
    </Modal>
  );
}
