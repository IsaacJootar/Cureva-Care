"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { getNotificationPrefs, updateNotificationPref, type NotificationPref } from "@/lib/ops";
import { AppShell } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/Card";
import { SelectField } from "@/components/ui/Field";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { useToast } from "@/components/ui/Toast";

const TYPE_LABEL: Record<string, string> = {
  stale_facility_alert: "Stale-facility alerts",
};

export default function NotificationsPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [prefs, setPrefs] = useState<NotificationPref[] | null>(null);

  const load = useCallback(() => {
    if (!user) return;
    getNotificationPrefs(user.id).then(setPrefs).catch(() => setPrefs([]));
  }, [user]);

  useEffect(() => {
    load();
  }, [load]);

  async function change(type: string, channel: string) {
    if (!user) return;
    try {
      await updateNotificationPref(user.id, type, channel);
      toast.success("Preference updated.");
      load();
    } catch {
      toast.error("Could not update.");
    }
  }

  return (
    <AppShell title="Notification preferences" subtitle="Choose how you receive each notification — for your own account">
      {!prefs ? (
        <div style={{ maxWidth: 560 }}><StatTileSkeleton /></div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 560 }}>
          {prefs.map((p) => (
            <Card key={p.id} padding="14px 16px">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
                <div>
                  <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>{TYPE_LABEL[p.notification_type] ?? p.notification_type}</div>
                  <div style={{ fontSize: 11, color: "var(--cv-text-muted)" }}>How you'd like to be notified.</div>
                </div>
                <div style={{ width: 200 }}>
                  <SelectField id={`pref-${p.id}`} value={p.channel} onChange={(e) => change(p.notification_type, e.target.value)}>
                    <option value="email_and_sms">Email and SMS</option>
                    <option value="email">Email only</option>
                    <option value="sms">SMS only</option>
                    <option value="none">None</option>
                  </SelectField>
                </div>
              </div>
            </Card>
          ))}
          <p style={{ fontSize: 11, color: "var(--cv-text-muted)" }}>
            There is no password to manage — sign-in is magic-link or your organisation&apos;s SSO.
          </p>
        </div>
      )}
    </AppShell>
  );
}
