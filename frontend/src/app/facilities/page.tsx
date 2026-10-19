"use client";

import { useEffect, useMemo, useState } from "react";
import { getFacilitiesOverview, type FacilityRow } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { EmptyState, StatusPill, StatTileSkeleton } from "@/components/ui/Feedback";
import { Table, Td, Th } from "@/components/ui/Table";
import { BuildingIcon } from "@/components/icons";

interface WardGroup {
  key: string;
  ward: string;
  lga: string;
  state: string;
  facilities: FacilityRow[];
}

export default function FacilitiesPage() {
  const [data, setData] = useState<{ facilities: FacilityRow[]; stale_days: number } | null>(null);

  useEffect(() => {
    getFacilitiesOverview().then(setData).catch(() => setData({ facilities: [], stale_days: 14 }));
  }, []);

  // Facility-first: each facility sits under its ward; wards roll up to LGA and State.
  const groups: WardGroup[] = useMemo(() => {
    if (!data) return [];
    const map = new Map<string, WardGroup>();
    for (const f of data.facilities) {
      const state = f.state ?? "—", lga = f.lga ?? "—", ward = f.ward ?? "—";
      const key = `${state}|${lga}|${ward}`;
      if (!map.has(key)) map.set(key, { key, ward, lga, state, facilities: [] });
      map.get(key)!.facilities.push(f);
    }
    return [...map.values()].sort((a, b) =>
      a.state.localeCompare(b.state) || a.lga.localeCompare(b.lga) || a.ward.localeCompare(b.ward),
    );
  }, [data]);

  const counts = useMemo(() => {
    if (!data) return "";
    const wards = new Set(data.facilities.map((f) => `${f.state}|${f.lga}|${f.ward}`));
    const lgas = new Set(data.facilities.map((f) => `${f.state}|${f.lga}`));
    const states = new Set(data.facilities.map((f) => f.state));
    return `${data.facilities.length} facilities · ${wards.size} wards · ${lgas.size} LGAs · ${states.size} states`;
  }, [data]);

  return (
    <AppShell
      title="Facilities"
      subtitle={data ? counts : "Loading…"}
      allowedRoles={["facility_lead", "organisation_user"]}
    >
      {!data ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
          {Array.from({ length: 3 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : data.facilities.length === 0 ? (
        <EmptyState icon={<BuildingIcon size={24} />} heading="No facilities in scope" />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {groups.map((g) => (
            <div key={g.key}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 8 }}>
                <h2 style={{ fontSize: 14, color: "var(--cv-text-primary)", margin: 0 }}>{g.ward} Ward</h2>
                <span style={{ fontSize: 11.5, color: "var(--cv-text-muted)" }}>{g.lga} · {g.state}</span>
                <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--cv-text-muted)" }}>
                  {g.facilities.length} facilit{g.facilities.length === 1 ? "y" : "ies"}
                </span>
              </div>
              <Table>
                <thead>
                  <tr>
                    <Th>Facility</Th>
                    <Th>Records</Th>
                    <Th>Births</Th>
                    <Th>Referrals awaiting</Th>
                    <Th>Reporting</Th>
                  </tr>
                </thead>
                <tbody>
                  {g.facilities.map((f) => (
                    <tr key={f.id}>
                      <Td style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{f.name}</Td>
                      <Td><span className="cv-num">{f.verified_records}</span></Td>
                      <Td><span className="cv-num">{f.deliveries}</span></Td>
                      <Td><span className="cv-num">{f.open_referrals}</span></Td>
                      <Td>
                        {f.is_stale ? (
                          <StatusPill status="danger">Not reporting (&gt;{data.stale_days}d)</StatusPill>
                        ) : (
                          <StatusPill status="success">Current</StatusPill>
                        )}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
