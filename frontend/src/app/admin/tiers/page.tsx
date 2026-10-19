"use client";

import { useEffect, useMemo, useState } from "react";
import { listTiers, updateTier } from "@/lib/ops";
import type { IntelModule, SubscriptionTier } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { useToast } from "@/components/ui/Toast";
import { CheckIcon, LayersIcon } from "@/components/icons";

export default function TiersPage() {
  const [modules, setModules] = useState<IntelModule[] | null>(null);
  const [tiers, setTiers] = useState<SubscriptionTier[] | null>(null);

  useEffect(() => {
    listTiers()
      .then((d) => {
        setModules(d.modules);
        setTiers([...d.tiers].sort((a, b) => a.order - b.order));
      })
      .catch(() => {
        setModules([]);
        setTiers([]);
      });
  }, []);

  return (
    <AppShell
      title="Plans & modules"
      subtitle="Decide which intelligence each plan includes. Subscribers see only the modules their plan unlocks."
      allowedRoles={["systems_admin"]}
    >
      {!tiers || !modules ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 14, maxWidth: 760 }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <StatTileSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 760 }}>
          {tiers.map((t) => (
            <TierCard key={t.id} tier={t} modules={modules} />
          ))}
        </div>
      )}
    </AppShell>
  );
}

function TierCard({ tier, modules }: { tier: SubscriptionTier; modules: IntelModule[] }) {
  const toast = useToast();
  const [selected, setSelected] = useState<Set<string>>(new Set(tier.modules));
  const [saving, setSaving] = useState(false);

  const baseline = useMemo(() => new Set(tier.modules), [tier.modules]);
  const dirty = useMemo(() => {
    if (selected.size !== baseline.size) return true;
    for (const k of selected) if (!baseline.has(k)) return true;
    return false;
  }, [selected, baseline]);

  function toggle(key: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function save() {
    setSaving(true);
    try {
      await updateTier(tier.id, { modules: [...selected] });
      toast.success(`${tier.name} plan updated.`);
      tier.modules = [...selected]; // keep baseline in sync without a refetch
    } catch {
      toast.error("Could not save the plan.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card padding="16px 18px">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 30,
              height: 30,
              borderRadius: 8,
              background: "var(--cv-accent-soft, rgba(99,102,241,0.12))",
              color: "var(--cv-accent, #6366f1)",
            }}
          >
            <LayersIcon size={16} />
          </span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--cv-text-primary)" }}>{tier.name}</div>
            <div style={{ fontSize: 11.5, color: "var(--cv-text-muted)" }}>
              {selected.size} module{selected.size === 1 ? "" : "s"} included
            </div>
          </div>
        </div>
        <Button onClick={save} loading={saving} disabled={!dirty} style={{ padding: "7px 14px", fontSize: 12 }}>
          {dirty ? "Save changes" : "Saved"}
        </Button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 8 }}>
        {modules.map((m) => {
          const on = selected.has(m.key);
          return (
            <button
              key={m.key}
              onClick={() => toggle(m.key)}
              aria-pressed={on}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 9,
                padding: "9px 11px",
                borderRadius: 8,
                border: `1px solid ${on ? "var(--cv-accent, #6366f1)" : "var(--cv-card-border)"}`,
                background: on ? "var(--cv-accent-soft, rgba(99,102,241,0.08))" : "var(--cv-input-bg)",
                color: "var(--cv-text-primary)",
                cursor: "pointer",
                textAlign: "left",
                fontSize: 12.5,
                transition: "border-color .12s, background .12s",
              }}
            >
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 18,
                  height: 18,
                  borderRadius: 5,
                  flexShrink: 0,
                  border: `1.5px solid ${on ? "var(--cv-accent, #6366f1)" : "var(--cv-input-border)"}`,
                  background: on ? "var(--cv-accent, #6366f1)" : "transparent",
                  color: "#fff",
                }}
              >
                {on && <CheckIcon size={12} />}
              </span>
              {m.label}
            </button>
          );
        })}
      </div>
    </Card>
  );
}
