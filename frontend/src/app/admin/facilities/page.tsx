"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import type { Facility } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Dialog";
import { TextField } from "@/components/ui/Field";
import { StatusPill } from "@/components/ui/Feedback";
import { EmptyState, StatTileSkeleton } from "@/components/ui/Feedback";
import { Table, Td, Th } from "@/components/ui/Table";
import { GeoCascade, type GeoSelection } from "@/components/geo";
import { useToast } from "@/components/ui/Toast";
import { BuildingIcon, PlusIcon } from "@/components/icons";

interface Paginated<T> {
  count: number;
  results: T[];
}

function asList<T>(data: Paginated<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results;
}

export default function FacilitiesPage() {
  const toast = useToast();
  const [facilities, setFacilities] = useState<Facility[] | null>(null);
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await apiGet<Paginated<Facility> | Facility[]>("/facilities");
      setFacilities(asList(data));
    } catch {
      setFacilities([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const regionCount = new Set(facilities?.map((f) => f.state_name).filter(Boolean)).size;
  const subtitle = facilities
    ? `${facilities.length} facilit${facilities.length === 1 ? "y" : "ies"} · ${regionCount} state${regionCount === 1 ? "" : "s"}`
    : "Loading…";

  return (
    <AppShell
      title="Manage facilities"
      subtitle={subtitle}
      allowedRoles={["systems_admin"]}
      action={
        <Button leftIcon={<PlusIcon size={15} />} onClick={() => setOpen(true)}>
          Add facility
        </Button>
      }
    >
      {facilities === null ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
          <StatTileSkeleton />
          <StatTileSkeleton />
          <StatTileSkeleton />
        </div>
      ) : facilities.length === 0 ? (
        <EmptyState
          icon={<BuildingIcon size={24} />}
          heading="No facilities yet"
          hint="Create the first facility by walking the State → LGA → Ward picker."
          action={
            <Button leftIcon={<PlusIcon size={15} />} onClick={() => setOpen(true)}>
              Add facility
            </Button>
          }
        />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Facility</Th>
              <Th>Region</Th>
              <Th>Template</Th>
              <Th>Last intake</Th>
              <Th>Completeness</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {facilities.map((f) => (
              <tr key={f.id}>
                <Td style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{f.name}</Td>
                <Td>{[f.state_name, f.local_government_name].filter(Boolean).join(" · ")}</Td>
                <Td style={{ color: "var(--cv-text-muted)" }}>—</Td>
                <Td style={{ color: "var(--cv-text-muted)" }}>—</Td>
                <Td style={{ color: "var(--cv-text-muted)" }}>—</Td>
                <Td>
                  {f.is_active ? (
                    <StatusPill status="success">Active</StatusPill>
                  ) : (
                    <StatusPill status="neutral">Inactive</StatusPill>
                  )}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <AddFacilityModal
        open={open}
        onClose={() => setOpen(false)}
        onCreated={(name) => {
          setOpen(false);
          toast.success(`Facility “${name}” added.`);
          void load();
        }}
      />
    </AppShell>
  );
}

function AddFacilityModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (name: string) => void;
}) {
  const [sel, setSel] = useState<GeoSelection | null>(null);
  const [name, setName] = useState("");
  const [facilityType, setFacilityType] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();

  const canSave = !!sel?.wardId && name.trim().length > 0;

  async function save() {
    if (!canSave || !sel) return;
    setSaving(true);
    setError(undefined);
    try {
      await apiPost("/facilities", {
        name: name.trim(),
        ward: sel.wardId,
        facility_type: facilityType.trim() || null,
      });
      setName("");
      setFacilityType("");
      setSel(null);
      onCreated(name.trim());
    } catch {
      setError("Could not create the facility. Check the details and try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} width={460}>
      <h2 style={{ fontSize: 16, color: "var(--cv-text-primary)", margin: "0 0 4px" }}>Add facility</h2>
      <p style={{ fontSize: 12, color: "var(--cv-text-muted)", margin: "0 0 18px" }}>
        Every facility belongs to a Ward — choose State, then LGA, then Ward.
      </p>

      <GeoCascade onChange={setSel} />

      <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 12 }}>
        <TextField
          id="facility-name"
          label="Facility name"
          placeholder="e.g. Gama Primary Health Centre"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <TextField
          id="facility-type"
          label="Facility type (optional)"
          placeholder="e.g. PHC, General hospital, Maternity home"
          value={facilityType}
          onChange={(e) => setFacilityType(e.target.value)}
        />
      </div>

      {error && (
        <div style={{ color: "var(--cv-danger-text)", fontSize: 11.5, marginTop: 12 }}>{error}</div>
      )}

      <div style={{ display: "flex", gap: 10, marginTop: 20, justifyContent: "flex-end" }}>
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={save} disabled={!canSave} loading={saving} loadingLabel="Saving…">
          Save facility
        </Button>
      </div>
    </Modal>
  );
}
