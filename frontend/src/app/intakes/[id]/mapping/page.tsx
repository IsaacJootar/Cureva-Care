"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { addAlias, getMapping, type MappingData } from "@/lib/templates";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SelectField } from "@/components/ui/Field";
import { EmptyState } from "@/components/ui/Feedback";
import { useToast } from "@/components/ui/Toast";
import { CheckIcon } from "@/components/icons";

// Systems-admin template-mapping screen for one intake (cureva-docs/03
// "Template-mapping admin screen"): map each unmatched label to a canonical
// field and save it as an alias — which writes a NEW template version.
export default function MappingPage() {
  const params = useParams<{ id: string }>();
  const intakeId = params.id;
  const toast = useToast();
  const [data, setData] = useState<MappingData | null>(null);

  const load = useCallback(() => {
    getMapping(intakeId).then(setData).catch(() => setData(null));
  }, [intakeId]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <AppShell
      title="Map register fields"
      subtitle={data ? `${data.facility_name} · ${data.register_family}` : "Loading…"}
      allowedRoles={["systems_admin"]}
    >
      {data === null ? (
        <p style={{ color: "var(--cv-text-muted)", fontSize: 12.5 }}>Loading…</p>
      ) : data.unmatched_labels.length === 0 ? (
        <EmptyState icon={<CheckIcon size={24} />} heading="Nothing to map" hint="Every extracted label matched the template." />
      ) : (
        <div style={{ maxWidth: 640, margin: "0 auto", display: "flex", flexDirection: "column", gap: 12 }}>
          <p style={{ fontSize: 12.5, color: "var(--cv-text-secondary)" }}>
            These labels were read from the page but didn&apos;t match the resolved template. Map each to a canonical
            field and save it as an alias — this creates a new template version; prior intakes keep their version.
          </p>
          {data.unmatched_labels.map((label) => (
            <MapRow
              key={label}
              label={label}
              templateId={data.template_id}
              fields={data.canonical_fields}
              onSaved={() => {
                toast.success(`“${label}” mapped.`);
                load();
              }}
            />
          ))}
        </div>
      )}
    </AppShell>
  );
}

function MapRow({
  label,
  templateId,
  fields,
  onSaved,
}: {
  label: string;
  templateId: string | null;
  fields: { canonical_field: string; label: string }[];
  onSaved: () => void;
}) {
  const [canonical, setCanonical] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function save() {
    if (!canonical || !templateId) return;
    setBusy(true);
    try {
      await addAlias(templateId, canonical, label);
      onSaved();
    } catch {
      toast.error("Could not save the alias.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card padding="14px 16px">
      <div style={{ display: "flex", alignItems: "flex-end", gap: 12 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.4px", color: "var(--cv-text-muted)", fontWeight: 600, marginBottom: 5 }}>
            Unmatched label
          </div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--cv-text-primary)" }}>{label}</div>
        </div>
        <div style={{ flex: 1.3 }}>
          <SelectField id={`map-${label}`} label="Map to canonical field" value={canonical} onChange={(e) => setCanonical(e.target.value)}>
            <option value="">Choose a field…</option>
            {fields.map((f) => (
              <option key={f.canonical_field} value={f.canonical_field}>{f.label}</option>
            ))}
          </SelectField>
        </div>
        <Button onClick={save} disabled={!canonical} loading={busy} loadingLabel="Saving…">
          Save as alias
        </Button>
      </div>
    </Card>
  );
}
