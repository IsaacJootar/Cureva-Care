"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { apiPatch } from "@/lib/api";
import { changePassword } from "@/lib/ops";
import { useAuth } from "@/lib/auth";
import type { CurrentUser } from "@/lib/types";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Dialog";
import { TextField } from "../ui/Field";
import { useToast } from "../ui/Toast";
import { BellIcon, EditIcon, LogOutIcon } from "../icons";

const ROLE_LABEL: Record<CurrentUser["role"], string> = {
  systems_admin: "Systems admin",
  facility_lead: "Facility lead",
  organisation_user: "Organisation user",
  data_officer: "Data officer",
};

// The account menu behind every sidebar's user footer (cureva-docs/09 "Account
// menu"): Profile (self-editable name, read-only email), Notification
// preferences, Change password, Sign out.
export function AccountMenu({ user }: { user: CurrentUser }) {
  const { signOut, setUser } = useAuth();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user.name);
  const [saving, setSaving] = useState(false);
  const [pwOpen, setPwOpen] = useState(false);
  const [cur, setCur] = useState("");
  const [nw, setNw] = useState("");
  const [pwSaving, setPwSaving] = useState(false);
  const [pwErr, setPwErr] = useState<string>();
  const ref = useRef<HTMLDivElement>(null);

  async function savePassword() {
    if (nw.length < 8) { setPwErr("New password must be at least 8 characters."); return; }
    setPwSaving(true);
    setPwErr(undefined);
    try {
      await changePassword(cur, nw);
      toast.success("Password changed.");
      setPwOpen(false);
      setCur(""); setNw("");
    } catch {
      setPwErr("Couldn't change password — check your current password.");
    } finally {
      setPwSaving(false);
    }
  }

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setEditing(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  async function saveName() {
    setSaving(true);
    try {
      const updated = await apiPatch<CurrentUser>("/users/me", { name: name.trim() });
      setUser(updated);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          width: "100%",
          padding: "10px 8px",
          borderTop: "1px solid rgba(255,255,255,0.08)",
          background: "none",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span style={{ width: 30, height: 30, borderRadius: "50%", background: "rgba(255,255,255,0.1)", color: "var(--cv-text-on-dark)", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 600, flexShrink: 0 }}>
          {user.name.slice(0, 1).toUpperCase()}
        </span>
        <span style={{ flex: 1, minWidth: 0 }}>
          <span style={{ display: "block", color: "var(--cv-text-on-dark)", fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user.name}</span>
          <span style={{ display: "block", color: "var(--cv-text-on-dark-muted)", fontSize: 10.5 }}>{ROLE_LABEL[user.role]}</span>
        </span>
      </button>

      {open && (
        <div style={{ position: "absolute", bottom: "calc(100% + 6px)", left: 0, width: 230, background: "var(--cv-card-bg)", border: "1px solid var(--cv-card-border)", borderRadius: 10, boxShadow: "var(--cv-menu-shadow)", padding: 12, zIndex: 100 }}>
          <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.4px", color: "var(--cv-text-muted)", fontWeight: 600, marginBottom: 6 }}>Profile</div>
          {editing ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <TextField id="acct-name" value={name} onChange={(e) => setName(e.target.value)} />
              <div style={{ display: "flex", gap: 6 }}>
                <Button variant="secondary" onClick={() => { setEditing(false); setName(user.name); }} style={{ padding: "5px 10px", fontSize: 11 }}>Cancel</Button>
                <Button onClick={saveName} loading={saving} style={{ padding: "5px 10px", fontSize: 11 }}>Save</Button>
              </div>
            </div>
          ) : (
            <button onClick={() => setEditing(true)} style={{ display: "flex", alignItems: "center", gap: 7, width: "100%", background: "none", border: "none", cursor: "pointer", padding: "4px 0", color: "var(--cv-text-primary)", fontSize: 12.5 }}>
              <span style={{ flex: 1, textAlign: "left" }}>{user.name}</span>
              <EditIcon size={13} />
            </button>
          )}
          <div style={{ fontSize: 11, color: "var(--cv-text-muted)", marginBottom: 10 }}>{user.email}</div>

          <Link href="/settings/notifications" onClick={() => setOpen(false)} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0", textDecoration: "none", color: "var(--cv-text-primary)", fontSize: 12.5, borderTop: "1px solid var(--cv-hairline)" }}>
            <BellIcon size={14} /> Notification preferences
          </Link>

          <button onClick={() => { setOpen(false); setPwOpen(true); }} style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "8px 0", background: "none", border: "none", borderTop: "1px solid var(--cv-hairline)", cursor: "pointer", color: "var(--cv-text-primary)", fontSize: 12.5 }}>
            <EditIcon size={14} /> Change password
          </button>

          <button onClick={signOut} style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "8px 0", background: "none", border: "none", borderTop: "1px dashed var(--cv-hairline)", cursor: "pointer", color: "var(--cv-button-danger-bg)", fontSize: 12.5, marginTop: 4 }}>
            <LogOutIcon size={14} /> Sign out
          </button>
        </div>
      )}

      {pwOpen && (
        <Modal open onClose={() => setPwOpen(false)} width={400}>
          <h2 style={{ fontSize: 16, color: "var(--cv-text-primary)", margin: "0 0 14px" }}>Change password</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <TextField id="cur-pw" label="Current password" type="password" value={cur} onChange={(e) => setCur(e.target.value)} />
            <TextField id="new-pw" label="New password" type="password" placeholder="At least 8 characters" value={nw} onChange={(e) => { setNw(e.target.value); if (pwErr) setPwErr(undefined); }} />
          </div>
          {pwErr && <div style={{ color: "var(--cv-danger-text)", fontSize: 11.5, marginTop: 10 }}>{pwErr}</div>}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 18 }}>
            <Button variant="secondary" onClick={() => setPwOpen(false)}>Cancel</Button>
            <Button onClick={savePassword} loading={pwSaving} disabled={!cur || !nw}>Change password</Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
