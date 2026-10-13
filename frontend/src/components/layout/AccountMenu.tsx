"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { apiPatch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { CurrentUser } from "@/lib/types";
import { Button } from "../ui/Button";
import { TextField } from "../ui/Field";
import { BellIcon, EditIcon, LogOutIcon } from "../icons";

const ROLE_LABEL: Record<CurrentUser["role"], string> = {
  systems_admin: "Systems admin",
  facility_lead: "Facility lead",
  organisation_user: "Organisation user",
  data_officer: "Data officer",
};

// The account menu behind every sidebar's user footer (cureva-docs/09 "Account
// menu"): Profile (self-editable name, read-only email), Notification
// preferences, Sign out. There is no password anywhere — sign-in is magic-link
// or SSO only.
export function AccountMenu({ user }: { user: CurrentUser }) {
  const { signOut, setUser } = useAuth();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user.name);
  const [saving, setSaving] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

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

          <button onClick={signOut} style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "8px 0", background: "none", border: "none", borderTop: "1px dashed var(--cv-hairline)", cursor: "pointer", color: "var(--cv-button-danger-bg)", fontSize: 12.5, marginTop: 4 }}>
            <LogOutIcon size={14} /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}
