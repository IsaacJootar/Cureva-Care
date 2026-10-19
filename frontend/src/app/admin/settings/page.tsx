"use client";

import { useEffect, useState } from "react";
import { listSettings, updateSetting, type PlatformSetting } from "@/lib/ops";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { Toggle } from "@/components/ui/Toggle";
import { useToast } from "@/components/ui/Toast";

export default function SettingsPage() {
  const [settings, setSettings] = useState<PlatformSetting[] | null>(null);

  useEffect(() => {
    listSettings().then(setSettings).catch(() => setSettings([]));
  }, []);

  return (
    <AppShell title="Settings" subtitle="Every tunable value in the platform, in one place" allowedRoles={["systems_admin"]}>
      {!settings ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 680, margin: "0 auto" }}>
          {Array.from({ length: 3 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 680, margin: "0 auto" }}>
          {settings.map((s) => (
            <SettingRow key={s.key} setting={s} />
          ))}
        </div>
      )}
    </AppShell>
  );
}

function SettingRow({ setting }: { setting: PlatformSetting }) {
  const toast = useToast();
  const [value, setValue] = useState<string>(String(setting.value));
  const [boolValue, setBoolValue] = useState<boolean>(Boolean(setting.value));
  const [saving, setSaving] = useState(false);

  async function save(v: unknown) {
    setSaving(true);
    try {
      await updateSetting(setting.key, v);
      toast.success(`${setting.key} updated — takes effect immediately.`);
    } catch {
      toast.error("Could not save — check the value matches the type.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card padding="14px 16px">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>{setting.key}</div>
          <div style={{ fontSize: 11.5, color: "var(--cv-text-muted)", marginTop: 3 }}>{setting.description}</div>
          <div style={{ fontSize: 10.5, color: "var(--cv-text-muted)", marginTop: 4 }}>Default: {String(setting.default)} · Type: {setting.value_type}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
          {setting.value_type === "boolean" ? (
            <Toggle checked={boolValue} onChange={(v) => { setBoolValue(v); save(v); }} ariaLabel={setting.key} />
          ) : (
            <>
              <input
                type={setting.value_type === "string" ? "text" : "number"}
                step={setting.value_type === "decimal" ? "0.01" : "1"}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                style={{ width: 90, padding: "7px 9px", borderRadius: 7, border: "1px solid var(--cv-input-border)", background: "var(--cv-input-bg)", color: "var(--cv-text-primary)", fontSize: 12.5 }}
              />
              <Button onClick={() => save(value)} loading={saving} style={{ padding: "7px 12px", fontSize: 12 }}>Save</Button>
            </>
          )}
        </div>
      </div>
    </Card>
  );
}
