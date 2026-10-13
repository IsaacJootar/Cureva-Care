"use client";

import { useEffect, useState } from "react";
import { getFacilitiesOverview, type FacilityRow } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { EmptyState, StatusPill, StatTileSkeleton } from "@/components/ui/Feedback";
import { Table, Td, Th } from "@/components/ui/Table";
import { BuildingIcon } from "@/components/icons";

export default function FacilitiesPage() {
  const [data, setData] = useState<{ facilities: FacilityRow[]; stale_days: number } | null>(null);

  useEffect(() => {
    getFacilitiesOverview().then(setData).catch(() => setData({ facilities: [], stale_days: 14 }));
  }, []);

  return (
    <AppShell
      title="Facilities"
      subtitle={data ? `${data.facilities.length} facilities · reporting, quality, comparison` : "Loading…"}
      allowedRoles={["facility_lead", "organisation_user"]}
    >
      {!data ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
          {Array.from({ length: 3 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : data.facilities.length === 0 ? (
        <EmptyState icon={<BuildingIcon size={24} />} heading="No facilities in scope" />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Facility</Th>
              <Th>Region</Th>
              <Th>Verified records</Th>
              <Th>Deliveries</Th>
              <Th>Open referrals</Th>
              <Th>Reporting</Th>
            </tr>
          </thead>
          <tbody>
            {data.facilities.map((f) => (
              <tr key={f.id}>
                <Td style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{f.name}</Td>
                <Td>{f.region}</Td>
                <Td><span className="cv-num">{f.verified_records}</span></Td>
                <Td><span className="cv-num">{f.deliveries}</span></Td>
                <Td><span className="cv-num">{f.open_referrals}</span></Td>
                <Td>
                  {f.is_stale ? (
                    <StatusPill status="danger">Stale (&gt;{data.stale_days}d)</StatusPill>
                  ) : (
                    <StatusPill status="success">Current</StatusPill>
                  )}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </AppShell>
  );
}
