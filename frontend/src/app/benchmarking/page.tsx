"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getBenchmarking, getEquity, getGeo,
  type Benchmarking, type Equity, type GeoRollup, type MetricDef,
} from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { SelectField } from "@/components/ui/Field";
import { ChartCard, LeagueTable, MetricMeter, type LeagueRow } from "@/components/ui/Charts";
import { NigeriaMap, type MapDatum } from "@/components/dashboard/NigeriaMap";

const NOTE = "Recorded activity, not population rates. Small samples flagged.";

function fmtRate(rate: number | null, num: number, den: number | null) {
  if (rate == null) return "no data";
  return `${Math.round(rate * 100)}% (${num}/${den})`;
}

export default function BenchmarkingPage() {
  const [metric, setMetric] = useState("deliveries");
  const [level, setLevel] = useState<"state" | "lga">("state");
  const [bench, setBench] = useState<Benchmarking | null>(null);
  const [geo, setGeo] = useState<GeoRollup | null>(null);
  const [stateGeo, setStateGeo] = useState<GeoRollup | null>(null);
  const [equity, setEquity] = useState<Equity | null>(null);

  const load = useCallback(() => {
    getBenchmarking(metric).then(setBench).catch(() => setBench(null));
    getGeo(metric, level).then(setGeo).catch(() => setGeo(null));
    getGeo(metric, "state").then(setStateGeo).catch(() => setStateGeo(null));
  }, [metric, level]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { getEquity().then(setEquity).catch(() => setEquity(null)); }, []);

  const metrics: MetricDef[] = bench?.available_metrics ?? [];
  const isRate = bench?.kind === "rate";

  const leagueRows: LeagueRow[] = (bench?.rows ?? []).map((r) => ({
    label: r.name,
    value: r.value ?? 0,
    display: isRate ? fmtRate(r.rate, r.numerator, r.denominator) : String(r.value ?? 0),
    sublabel: `${r.region}${r.low_confidence ? " · small sample" : ""}`,
  }));
  const geoRows: LeagueRow[] = (geo?.areas ?? []).map((a) => ({
    label: a.name,
    value: a.value ?? 0,
    display: isRate ? fmtRate(a.rate, a.numerator, a.denominator) : String(a.value ?? 0),
    sublabel: a.low_confidence ? "small sample" : undefined,
  }));
  const mapData: MapDatum[] = (stateGeo?.areas ?? []).map((a) => ({
    name: a.name,
    value: a.value,
    display: isRate ? fmtRate(a.rate, a.numerator, a.denominator) : String(a.value ?? 0),
  }));

  return (
    <AppShell
      title="Benchmarking & equity"
      subtitle="Compare facilities and regions, and see where care differs"
      allowedRoles={["facility_lead", "organisation_user"]}
      action={
        <div style={{ width: 230 }}>
          <SelectField id="metric" label="" value={metric} onChange={(e) => setMetric(e.target.value)}>
            {metrics.length === 0 && <option value="deliveries">Deliveries</option>}
            {metrics.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
          </SelectField>
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <ChartCard
          title={`Facility ranking — ${bench?.label ?? ""}`}
          subtitle="Highest to lowest across the facilities in your scope"
          note={NOTE}
          exportCsv={{
            name: `facility-ranking-${metric}`,
            header: ["Rank", "Facility", "Region", "Value", "Numerator", "Denominator"],
            rows: (bench?.rows ?? []).map((r, i) => [i + 1, r.name, r.region, r.value, r.numerator, r.denominator]),
          }}
        >
          <LeagueTable rows={leagueRows} maxRows={20} />
        </ChartCard>

        <ChartCard
          title={`Map — ${stateGeo?.label ?? bench?.label ?? ""} by State`}
          subtitle="Shaded by value; states with no data stay grey"
          note={NOTE}
          exportCsv={{
            name: `map-state-${metric}`,
            header: ["State", "Value", "Numerator", "Denominator"],
            rows: (stateGeo?.areas ?? []).map((a) => [a.name, a.value, a.numerator, a.denominator]),
          }}
        >
          <div style={{ maxWidth: 620, margin: "0 auto" }}>
            <NigeriaMap data={mapData} />
          </div>
        </ChartCard>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <ChartCard
            title={`By ${level === "state" ? "State" : "LGA"} — ${geo?.label ?? ""}`}
            subtitle="Totals by area"
            note={NOTE}
            action={
              <div style={{ display: "inline-flex", background: "var(--cv-bg)", borderRadius: "var(--cv-radius-pill)", padding: 2, border: "1px solid var(--cv-hairline)" }}>
                {(["state", "lga"] as const).map((l) => (
                  <button key={l} onClick={() => setLevel(l)} style={{
                    padding: "3px 10px", borderRadius: "var(--cv-radius-pill)", border: "none", cursor: "pointer",
                    fontSize: 10.5, fontWeight: 600, textTransform: "uppercase",
                    background: level === l ? "var(--cv-accent-solid)" : "transparent",
                    color: level === l ? "#fff" : "var(--cv-text-secondary)",
                  }}>{l}</button>
                ))}
              </div>
            }
            exportCsv={{
              name: `geo-${level}-${metric}`,
              header: [level, "Value", "Numerator", "Denominator"],
              rows: (geo?.areas ?? []).map((a) => [a.name, a.value, a.numerator, a.denominator]),
            }}
          >
            <LeagueTable rows={geoRows} maxRows={15} />
          </ChartCard>

          <ChartCard
            title="Fairness — care by number of past births"
            subtitle="Does care differ for first-time mothers vs. those with many births?"
            note="Based on what was recorded at check-ups; women with no number recorded are shown separately, never guessed."
          >
            {!equity || equity.bands.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No ANC parity data yet.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {equity.bands.map((b) => (
                  <div key={b.band} style={{ paddingBottom: 6 }}>
                    <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--cv-text-primary)", marginTop: 6 }}>
                      {b.band} <span className="cv-num" style={{ color: "var(--cv-text-muted)", fontWeight: 400 }}>· {b.contacts} check-ups</span>
                    </div>
                    <MetricMeter label="Tested (HIV, syphilis, anaemia)" ratio={b.screening_coverage} />
                    <MetricMeter label="Got preventives (iron, tetanus, malaria)" ratio={b.intervention_coverage} />
                  </div>
                ))}
              </div>
            )}
          </ChartCard>
        </div>
      </div>
    </AppShell>
  );
}
