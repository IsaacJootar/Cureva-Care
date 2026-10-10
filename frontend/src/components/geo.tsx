"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import type { Facility, GeoState, LocalGovernment, Ward } from "@/lib/types";
import { SelectField } from "./ui/Field";

export interface GeoSelection {
  stateId: string;
  lgaId: string;
  wardId: string;
  facilityId: string;
  labels: { state?: string; lga?: string; ward?: string; facility?: string };
}

const EMPTY: GeoSelection = { stateId: "", lgaId: "", wardId: "", facilityId: "", labels: {} };

// The guided State -> LGA -> Ward (-> Facility) picker used for facility
// creation and organisation access grants (cureva-docs/02 "Facility
// administrative hierarchy", 09 screens 3 & 7). Each level narrows the next.
export function GeoCascade({
  includeFacility = false,
  onChange,
}: {
  includeFacility?: boolean;
  onChange: (sel: GeoSelection) => void;
}) {
  const [states, setStates] = useState<GeoState[]>([]);
  const [lgas, setLgas] = useState<LocalGovernment[]>([]);
  const [wards, setWards] = useState<Ward[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [sel, setSel] = useState<GeoSelection>(EMPTY);

  useEffect(() => {
    apiGet<GeoState[]>("/states").then(setStates).catch(() => {});
  }, []);

  function emit(next: GeoSelection) {
    setSel(next);
    onChange(next);
  }

  async function pickState(stateId: string) {
    const label = states.find((s) => s.id === stateId)?.name;
    emit({ stateId, lgaId: "", wardId: "", facilityId: "", labels: { state: label } });
    setLgas([]);
    setWards([]);
    setFacilities([]);
    if (stateId) {
      setLgas(await apiGet<LocalGovernment[]>(`/states/${stateId}/local-governments`).catch(() => []));
    }
  }

  async function pickLga(lgaId: string) {
    const label = lgas.find((l) => l.id === lgaId)?.name;
    emit({ ...sel, lgaId, wardId: "", facilityId: "", labels: { ...sel.labels, lga: label, ward: undefined, facility: undefined } });
    setWards([]);
    setFacilities([]);
    if (lgaId) {
      setWards(await apiGet<Ward[]>(`/local-governments/${lgaId}/wards`).catch(() => []));
    }
  }

  async function pickWard(wardId: string) {
    const label = wards.find((w) => w.id === wardId)?.name;
    emit({ ...sel, wardId, facilityId: "", labels: { ...sel.labels, ward: label, facility: undefined } });
    setFacilities([]);
    if (wardId && includeFacility) {
      const all = await apiGet<{ results?: Facility[] } | Facility[]>("/facilities").catch(() => []);
      const list = Array.isArray(all) ? all : (all.results ?? []);
      setFacilities(list.filter((f) => f.ward === wardId));
    }
  }

  function pickFacility(facilityId: string) {
    const label = facilities.find((f) => f.id === facilityId)?.name;
    emit({ ...sel, facilityId, labels: { ...sel.labels, facility: label } });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <SelectField id="geo-state" label="State" value={sel.stateId} onChange={(e) => pickState(e.target.value)}>
        <option value="">Choose a state…</option>
        {states.map((s) => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </SelectField>

      <SelectField id="geo-lga" label="Local Government Area" value={sel.lgaId} onChange={(e) => pickLga(e.target.value)} disabled={!sel.stateId}>
        <option value="">{sel.stateId ? "Choose an LGA…" : "Select a state first"}</option>
        {lgas.map((l) => (
          <option key={l.id} value={l.id}>{l.name}</option>
        ))}
      </SelectField>

      <SelectField id="geo-ward" label="Ward" value={sel.wardId} onChange={(e) => pickWard(e.target.value)} disabled={!sel.lgaId}>
        <option value="">{sel.lgaId ? "Choose a ward…" : "Select an LGA first"}</option>
        {wards.map((w) => (
          <option key={w.id} value={w.id}>{w.name}</option>
        ))}
      </SelectField>

      {includeFacility && (
        <SelectField id="geo-facility" label="Facility (optional — leave blank to grant the whole ward)" value={sel.facilityId} onChange={(e) => pickFacility(e.target.value)} disabled={!sel.wardId}>
          <option value="">{sel.wardId ? "Whole ward" : "Select a ward first"}</option>
          {facilities.map((f) => (
            <option key={f.id} value={f.id}>{f.name}</option>
          ))}
        </SelectField>
      )}
    </div>
  );
}
