"use client";

import { useCallback, useEffect, useState } from "react";
import { getCoverage, type Coverage } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { SelectField } from "@/components/ui/Field";
import { ChartCard, LeagueTable, MetricMeter, type LeagueRow } from "@/components/ui/Charts";
import { NigeriaMap, type MapDatum } from "@/components/dashboard/NigeriaMap";

const YEARS = [2027, 2026, 2025, 2024];

function fmtRate(rate: number | null, num: number, den: number | null) {
  if (rate == null || den == null) return "no estimate";
  return `${Math.round(rate * 100)}% (${num} of ${den})`;
}

export default function CoveragePage() {
  const [year, setYear] = useState(2026);
  const [level, setLevel] = useState<"lga" | "state">("lga");
  const [indicator, setIndicator] = useState("anc1");
  const [cov, setCov] = useState<Coverage | null>(null);
  const [stateCov, setStateCov] = useState<Coverage | null>(null);

  const load = useCallback(() => {
    getCoverage({ year, level, indicator }).then(setCov).catch(() => setCov(null));
    getCoverage({ year, level: "state", indicator }).then(setStateCov).catch(() => setStateCov(null));
  }, [year, level, indicator]);
  useEffect(() => { load(); }, [load]);

  const catalogue = cov?.indicator_catalogue ?? [
    { key: "anc1", label: "Women who registered a pregnancy" },
    { key: "anc4", label: "Women who reached 4+ check-ups" },
    { key: "sba", label: "Women who gave birth in a facility" },
    { key: "pnc", label: "Women who came back after birth" },
  ];
  const ind = cov?.indicators ?? {};
  const selectedLabel = catalogue.find((c) => c.key === indicator)?.label ?? "";

  const leagueRows: LeagueRow[] = (cov?.areas ?? []).map((a) => ({
    label: a.name,
    value: a.rate ?? -1,
    display: fmtRate(a.rate, a.numerator, a.denominator),
    sublabel: a.has_denominator ? undefined : "no population estimate loaded",
  }));
  const mapData: MapDatum[] = (stateCov?.areas ?? []).map((a) => ({
    name: a.name,
    value: a.rate,
    display: fmtRate(a.rate, a.numerator, a.denominator),
  }));

  const sources = cov?.sources ?? [];
  const missing = cov?.areas_missing_denominator ?? [];
  const estimateNote =
    `Coverage compares recorded activity to an estimated number of expected pregnancies/births — these are estimates` +
    (sources.length ? `, from ${sources.join(", ")}` : "") + ".";

  return (
    <AppShell
      title="Coverage & reach"
      subtitle="What share of the women expected in an area are we actually reaching?"
      allowedRoles={["facility_lead", "organisation_user"]}
      action={
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{ width: 150 }}>
            <SelectField id="indicator" label="" value={indicator} onChange={(e) => setIndicator(e.target.value)}>
              {catalogue.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
            </SelectField>
          </div>
          <div style={{ width: 100 }}>
            <SelectField id="year" label="" value={String(year)} onChange={(e) => setYear(Number(e.target.value))}>
              {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
            </SelectField>
          </div>
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Estimate disclosure */}
        <div style={{ fontSize: 11.5, color: "var(--cv-text-muted)", background: "var(--cv-accent-soft)", border: "1px solid var(--cv-card-border)", borderRadius: 9, padding: "9px 12px" }}>
          {estimateNote}
          {missing.length > 0 && (
            <> No estimate is loaded yet for: <strong>{missing.join(", ")}</strong> — those areas show no rate.</>
          )}
        </div>

        <ChartCard title={`Coverage this year (${year})`} subtitle="Recorded activity as a share of the expected number — across areas with a loaded estimate">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
            {catalogue.map((c) => (
              <div key={c.key}>
                <MetricMeter label={c.label} ratio={{ numerator: ind[c.key]?.numerator ?? 0, denominator: ind[c.key]?.denominator ?? 0, rate: ind[c.key]?.rate ?? null }} />
              </div>
            ))}
          </div>
        </ChartCard>

        <ChartCard
          title="Coverage by State"
          subtitle={`Shaded by "${selectedLabel}" — states with no loaded estimate stay grey`}
          exportCsv={{
            name: `coverage-state-${indicator}-${year}`,
            header: ["State", "Rate", "Numerator", "Denominator"],
            rows: (stateCov?.areas ?? []).map((a) => [a.name, a.rate, a.numerator, a.denominator]),
          }}
        >
          <NigeriaMap data={mapData} />
        </ChartCard>

        <ChartCard
          title={`Coverage by ${level === "state" ? "State" : "LGA"}`}
          subtitle={`"${selectedLabel}" — highest to lowest across your areas`}
          action={
            <div style={{ width: 150 }}>
              <SelectField id="level" label="" value={level} onChange={(e) => setLevel(e.target.value as "lga" | "state")}>
                <option value="lga">By LGA</option>
                <option value="state">By State</option>
              </SelectField>
            </div>
          }
          exportCsv={{
            name: `coverage-${level}-${indicator}-${year}`,
            header: [level === "state" ? "State" : "LGA", "Rate", "Numerator", "Denominator"],
            rows: (cov?.areas ?? []).map((a) => [a.name, a.rate, a.numerator, a.denominator]),
          }}
        >
          <LeagueTable rows={leagueRows} maxRows={20} />
        </ChartCard>
      </div>
    </AppShell>
  );
}
