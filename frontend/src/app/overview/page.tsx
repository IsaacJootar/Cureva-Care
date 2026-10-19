"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getWorkspace, type Workspace } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { Funnel, ChartPanel } from "@/components/ui/Charts";
import { TrendsPanel } from "@/components/dashboard/TrendsPanel";
import { StatTile } from "@/components/ui/StatTile";
import { StatTileSkeleton, StatusPill } from "@/components/ui/Feedback";
import { Table, Td, Th } from "@/components/ui/Table";
import { ActivityIcon, AlertTriangleIcon, BuildingIcon, CheckIcon, FileTextIcon, HeartPulseIcon } from "@/components/icons";

export default function OverviewPage() {
  const [ws, setWs] = useState<Workspace | null>(null);

  useEffect(() => {
    getWorkspace().then(setWs).catch(() => setWs(null));
  }, []);

  const isOrg = ws?.role === "organisation_user";
  const s = ws?.summary;

  const cj = useMemo(() => {
    if (!s) return [];
    return [
      { label: "Registered pregnancies", value: s.care_journey.booked_episodes },
      { label: "Pregnancy check-ups", value: s.care_journey.anc_contacts },
      { label: "Births", value: s.care_journey.deliveries },
      { label: "After-birth check-ups", value: s.care_journey.pnc_contacts },
    ];
  }, [s]);

  return (
    <AppShell
      title="Overview"
      subtitle={ws ? (isOrg ? scopeLine(ws.scope_breakdown) : "Your facility's operating picture") : "Loading…"}
      allowedRoles={["facility_lead", "organisation_user"]}
    >
      {!ws || !s ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
          {Array.from({ length: 4 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ display: "grid", gridTemplateColumns: `repeat(${isOrg ? 5 : 4}, 1fr)`, gap: 14 }}>
            {isOrg && (
              <StatTile status="neutral" icon={<BuildingIcon size={14} />} label="Facilities" value={ws.facility_count} />
            )}
            <StatTile status="success" icon={<CheckIcon size={14} />} label="Records captured" value={s.operational.verified_records} />
            <StatTile status="neutral" icon={<ActivityIcon size={14} />} label="Births" value={s.operational.deliveries} />
            <StatTile
              status={s.operational.open_referrals > 0 ? "warning" : "success"}
              icon={<AlertTriangleIcon size={14} />}
              label="Referrals awaiting outcome"
              value={s.operational.open_referrals}
            />
            <StatTile status="neutral" icon={<HeartPulseIcon size={14} />} label="After-birth check-ups" value={s.operational.pnc_contacts} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
            <ChartPanel title="The care journey">
              <Funnel stages={cj} />
            </ChartPanel>
            <ChartPanel title="Staying in care">
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <LinkageLine label="Pregnancy care → gave birth here" ratio={s.care_journey.delivery_linkage} />
                <LinkageLine label="Came back after birth" ratio={s.care_journey.postnatal_linkage} />
              </div>
            </ChartPanel>
          </div>

          <TrendsPanel />

          {ws.facilities.length > 1 && (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <h2 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: 0 }}>Facilities in your scope</h2>
                <Link href="/facilities" style={{ fontSize: 12, color: "var(--cv-accent-solid)" }}>View all facilities</Link>
              </div>
              <Table>
                <thead><tr><Th>Facility</Th><Th>Region</Th></tr></thead>
                <tbody>
                  {ws.facilities.slice(0, 5).map((f) => (
                    <tr key={f.id}>
                      <Td style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{f.name}</Td>
                      <Td>{f.region}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
}

function scopeLine(b?: { facilities: number; wards: number; lgas: number; states: number }): string {
  if (!b) return "Your scope";
  const p = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
  return `${p(b.facilities, "facility", "facilities")} · ${p(b.wards, "ward", "wards")} · ${p(b.lgas, "LGA", "LGAs")} · ${p(b.states, "state", "states")}`;
}

function LinkageLine({ label, ratio }: { label: string; ratio: { numerator: number; denominator: number; rate: number | null } }) {
  const pct = ratio.rate != null ? Math.round(ratio.rate * 100) : null;
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: "1px solid var(--cv-hairline)" }}>
      <span style={{ fontSize: 12.5, color: "var(--cv-text-secondary)" }}>{label}</span>
      <span>
        {pct != null ? <StatusPill status={pct >= 70 ? "success" : "warning"}>{pct}%</StatusPill> : <StatusPill status="neutral">No data</StatusPill>}
        <span className="cv-num" style={{ fontSize: 11, color: "var(--cv-text-muted)", marginLeft: 8 }}>
          {ratio.numerator}/{ratio.denominator}
        </span>
      </span>
    </div>
  );
}
