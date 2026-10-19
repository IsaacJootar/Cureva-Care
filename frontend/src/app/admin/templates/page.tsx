"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { RegisterFamily } from "@/lib/intake";
import { listTemplateFlags, listTemplates, type Template, type TemplateFlag } from "@/lib/templates";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card, CardTitle } from "@/components/ui/Card";
import { EmptyState, StatusPill } from "@/components/ui/Feedback";
import { Table, Td, Th } from "@/components/ui/Table";
import { AlertTriangleIcon, LayersIcon } from "@/components/icons";

const FAMILIES: { key: RegisterFamily; label: string }[] = [
  { key: "ANC", label: "Antenatal (ANC)" },
  { key: "Delivery", label: "Delivery" },
  { key: "PNC", label: "Postnatal (PNC)" },
];

export default function TemplatesPage() {
  const router = useRouter();
  const [family, setFamily] = useState<RegisterFamily>("ANC");
  const [templates, setTemplates] = useState<Template[] | null>(null);
  const [flags, setFlags] = useState<TemplateFlag[]>([]);

  useEffect(() => {
    listTemplates().then(setTemplates).catch(() => setTemplates([]));
    listTemplateFlags().then(setFlags).catch(() => setFlags([]));
  }, []);

  const familyTemplates = useMemo(
    () => (templates ?? []).filter((t) => t.register_family === family),
    [templates, family],
  );
  const sharedDefault = familyTemplates.find((t) => t.facility === null && t.is_active);
  const overrides = familyTemplates.filter((t) => t.facility !== null);

  return (
    <AppShell
      title="Templates"
      subtitle="Per-facility register templates, each falling back to a shared default"
      allowedRoles={["systems_admin"]}
    >
      {/* Family segmented control */}
      <div style={{ display: "inline-flex", background: "var(--cv-bg)", borderRadius: "var(--cv-radius-pill)", padding: 3, border: "1px solid var(--cv-hairline)", marginBottom: 18 }}>
        {FAMILIES.map((f) => (
          <button
            key={f.key}
            onClick={() => setFamily(f.key)}
            style={{
              padding: "7px 16px",
              borderRadius: "var(--cv-radius-pill)",
              border: "none",
              cursor: "pointer",
              fontSize: 12.5,
              fontWeight: 600,
              background: family === f.key ? "var(--cv-accent-solid)" : "transparent",
              color: family === f.key ? "#fff" : "var(--cv-text-secondary)",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 900, margin: "0 auto" }}>
        {/* Shared default */}
        <Card>
          <CardTitle right={sharedDefault ? <StatusPill status="success">Active · v{sharedDefault.version}</StatusPill> : undefined}>
            Shared default — {family}
          </CardTitle>
          {sharedDefault ? (
            <>
              <p style={{ fontSize: 11.5, color: "var(--cv-text-muted)", margin: "0 0 12px" }}>
                {sharedDefault.column_count} fields · effective {sharedDefault.effective_date} · used by every facility
                without its own override.
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {sharedDefault.schema.columns.map((c) => (
                  <span
                    key={c.canonical_field}
                    style={{
                      fontSize: 11,
                      padding: "3px 9px",
                      borderRadius: "var(--cv-radius-pill)",
                      background: "var(--cv-neutral-pill-bg)",
                      color: "var(--cv-neutral-pill-text)",
                    }}
                  >
                    {c.label}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <p style={{ fontSize: 12.5, color: "var(--cv-text-muted)" }}>No shared default registered for {family}.</p>
          )}
        </Card>

        {/* Facility-specific overrides */}
        <div>
          <h2 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", marginBottom: 10 }}>Facility-specific overrides</h2>
          {overrides.length === 0 ? (
            <EmptyState icon={<LayersIcon size={22} />} heading="No facility overrides" hint={`Every facility uses the shared ${family} default.`} />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Facility</Th>
                  <Th>Version</Th>
                  <Th>Fields</Th>
                  <Th>Effective</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {overrides.map((t) => (
                  <tr key={t.id}>
                    <Td style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{t.facility_name}</Td>
                    <Td><span className="cv-num">v{t.version}</span></Td>
                    <Td><span className="cv-num">{t.column_count}</span></Td>
                    <Td>{t.effective_date}</Td>
                    <Td>{t.is_active ? <StatusPill status="success">Active</StatusPill> : <StatusPill status="neutral">Superseded</StatusPill>}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </div>

        {/* Open flags awaiting admin review */}
        <div>
          <h2 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", marginBottom: 10 }}>Open flags — awaiting admin review</h2>
          {flags.length === 0 ? (
            <EmptyState icon={<AlertTriangleIcon size={22} />} heading="No open flags" hint="Data officers haven't flagged any register mismatches." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {flags.map((f) => (
                <div
                  key={f.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "11px 14px",
                    background: "var(--cv-warning-bg)",
                    border: "1px solid var(--cv-warning-border)",
                    borderRadius: 10,
                  }}
                >
                  <span style={{ color: "var(--cv-warning-icon)" }}><AlertTriangleIcon size={16} /></span>
                  <span style={{ flex: 1 }}>
                    <span style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>
                      {f.facility_name} · {f.register_family}
                    </span>
                    <span style={{ display: "block", fontSize: 11, color: "var(--cv-text-secondary)" }}>
                      {f.note || "No note"} — flagged by {f.flagged_by_name}
                    </span>
                  </span>
                  <Button variant="secondary" onClick={() => router.push(`/intakes/${f.intake}/mapping`)}>
                    Review &amp; map
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
