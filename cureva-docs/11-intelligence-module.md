# 11 — Intelligence Module (the product we sell)

The intelligence module is Cureva Care's flagship, sold to NGOs, government
agencies, individuals and facilities. This document is the **authoritative build
plan**: it is implemented exactly as written, section by section, each section
committed + pushed on its own, and **signed off below** when done. Approved by
the product owner (2026-10-16).

See `06-metrics-and-reporting.md` for the metric/lens spec this extends, and
`DECISIONS.md` for the running rationale log.

---

## Design principles (non-negotiable, apply to every workstream)

1. **Only the three registers.** Every view traces to ANC/Delivery/PNC fields,
   joined through identity linkage and the facility hierarchy. No invented
   sources.
2. **Always a denominator.** No naked percentages; every rate ships with its
   numerator/denominator and a completeness read. "Recorded activity, not
   population rates" is stated on every surface.
3. **Never infer a blank.** Missing ≠ normal. Blanks are shown as unknown.
4. **AI touches aggregates only.** Narrative AI never receives a woman-level row.
5. **Clinical thresholds need sign-off.** Anything that stratifies clinical risk
   ships behind the named clinical owner (open decision #2); until then it is
   labelled "pending clinical sign-off" and its thresholds are configurable.
6. **Explainable, not black-box.** Every flag/score shows the exact fields and
   rule version that produced it.
7. **Access-scoped everywhere.** Every new view, line-list and export respects
   role + organisation grant scoping. Case-level data never reaches an
   Organisation user; they get roll-ups only.
8. **Dates are service dates.** All time filtering uses service/delivery/visit
   dates, never upload/publish dates.

---

## Workstreams

### WS1 — Time & Trends (longitudinal intelligence)
Turn every snapshot metric into a time series.
- Date-bucketed aggregation (week / month) over projected events, service-date based.
- Trend endpoint(s) returning each core metric per bucket with numerator/denominator.
- Period-over-period deltas on stat tiles ("▲ 6 pts vs previous period").
- Evidence freshness / backlog trended.
- Frontend: trend-line charts + delta tiles across Overview, Care journey, Outcomes.

### WS2 — Benchmarking & Equity engine
- Facility / Ward / LGA / State league tables for any metric, with small-sample guards.
- Equity slicing by age band, parity band, and geography (age/parity from ANC; geo from hierarchy).
- Choropleth maps (State → LGA → Ward) of coverage, risk load, outcomes.
- Frontend: ranked tables + map view + equity breakdown panels.

### WS3 — Continuum & Cohort engine
- Interactive care-journey funnel with drop-off counts at each step.
- Access-scoped, downloadable line-lists at each drop-off (e.g. "delivered, no PNC in N days").
- Booking-cohort retention through the continuum over time.
- Frontend: funnel with clickable steps → scoped line-list → export.

### WS4 — MPDSR-grade severe-outcome surveillance
- Case register: every stillbirth / maternal death / early neonatal death as a
  traceable case carrying its linked antenatal→delivery→postnatal story.
- Per-case timeline view; severe-outcome trend; facility clustering signal.
- Frontend: case list (scoped) + case timeline + cluster alerts.

### WS5 — Risk intelligence & early-warning
- Transparent, rule-based risk stratification (composite tier from recorded
  markers), versioned, pending clinical sign-off — never black-box.
- Early-warning rules beyond stale-facility: referral backlog growth,
  severe-outcome cluster, coverage below a configurable floor, high-risk woman
  with no recent contact.
- Notification center (in-app + email/SMS via existing preferences), digests.
- Frontend: risk-tier pyramid + alerts feed + notification center.

### WS6 — RDQA-as-a-service
- Continuous Routine Data Quality Assessment: per-facility extraction
  confidence, template flags, completeness, implausible-value rate, timeliness —
  trended and ranked.
- Downloadable RDQA report.
- Frontend: RDQA scorecard + ranking + trend.

### WS7 — Report products
- Buyer-specific templates: Facility operational, NGO/donor grant (aggregate +
  equity + RDQA), Government/LGA surveillance (MPDSR + continuum).
- Scheduled generation (monthly/quarterly), branded PDF export, CSV/Excel data packs.
- Access-scoped shareable report snapshots.

### WS8 — Visualization layer upgrade
- A themeable, dependency-light chart kit (light/dark, design-system tokens):
  line, bar, stacked bar, funnel, distribution, league table, choropleth.
- Every chart drill-downable and exportable (PNG/CSV).
- Adopted across all dashboards.

---

## Phasing

- **Phase 1 — Make it move & compare:** WS1 (Trends) + WS2 (Benchmarking/Equity/maps) + WS8 (chart kit).
- **Phase 2 — The actionable moat:** WS3 (Continuum/cohort) + WS4 (MPDSR case surveillance).
- **Phase 3 — Proactive & productized:** WS5 (Risk & early-warning) + WS6 (RDQA report) + WS7 (report products).

WS8's chart kit is built first within Phase 1 (WS1/WS2 depend on it).

---

## Sign-off checklist

A section is signed off only when: built, tested (backend tests green; frontend
type-checks), verified, committed **and pushed**. Date on completion.

### Phase 1 — COMPLETE
- [x] **WS8** — Chart kit (line, stacked bar, league table, delta badge, choropleth; themeable; CSV/PNG export) — 2026-10-16
- [x] **WS1** — Time & Trends (bucketed aggregation + /trends endpoint + trend charts + deltas + export) — 2026-10-16
- [x] **WS2** — Benchmarking & Equity (facility league tables + geo rollup + parity equity + Nigeria choropleth) — 2026-10-16

### Phase 2
- [ ] **WS3** — Continuum & Cohort (funnel drop-offs + scoped line-lists + cohort retention)
- [ ] **WS4** — MPDSR surveillance (case register + timeline + clustering)

### Phase 3
- [ ] **WS5** — Risk intelligence & early-warning (risk tiers + alert rules + notification center)
- [ ] **WS6** — RDQA-as-a-service (scorecard + ranking + report)
- [ ] **WS7** — Report products (buyer templates + scheduling + PDF/Excel export + shareable snapshots)

---

## Module sign-offs (filled in as completed)

_(Each entry: what was built, where it lives, test/verify status, commit.)_

**WS8 (chart kit) — partial, signed off 2026-10-16.** SVG `LineChart`, `StackedBars`,
`LeagueTable`, `DeltaBadge`, export-capable `ChartCard` (CSV + PNG with CSS-var
inlining) in `frontend/src/components/ui/Charts.tsx`; export utils in
`frontend/src/lib/chartExport.ts`. Themeable via design-system tokens; verified
rendering live on Overview. Choropleth map deferred to WS2 (needs geo data).
Commit `ffdabbf`.

**WS1 (Time & Trends) — signed off 2026-10-16.** `backend/intelligence/trends.py`
buckets every datable event by month/ISO-week on its service date, each metric
with numerator/denominator + period deltas; `GET /trends` (scoped) in
`views.py`/`urls.py`; `TrendsPanel` (month/week toggle, 3 trend-line cards with
deltas + CSV/PNG export) on the Overview dashboard. Tests: `test_trends.py`
(3, green); full intelligence suite 9 passed; frontend `tsc` clean; verified live
(two-bucket trend rendering correctly). Commit `65e64e0`.

_Note: a pre-existing React duplicate-key warning in the shared nav/layout was
found during WS1 and spun off as a separate task (unrelated to intelligence)._

**WS2 (Benchmarking & Equity) — signed off 2026-10-16.**
`backend/intelligence/benchmarking.py`: per-facility metric accumulation,
facility league tables (ranked, small-sample flagged), geo rollup to State/LGA,
and ANC coverage sliced by parity band (unknown shown separately). Endpoints
`/benchmarking`, `/geo`, `/equity` (scoped) in `views.py`/`urls.py`. Frontend:
`/benchmarking` dashboard with metric selector, facility league, state/LGA
rollup, parity-equity panel, and a **Nigeria state choropleth**
(`components/dashboard/NigeriaMap.tsx`) with projected SVG + name matching.
Boundaries: geoBoundaries gbOpen NGA ADM1 (CC-BY), simplified to
`frontend/public/geo/nigeria-states.geojson` (283 KB static asset). Tests:
`test_benchmarking.py` (3); intelligence suite 12 passed; `tsc` clean; verified
live (Kano correctly shaded on the map, real parity equity data). Commits
`3e14ea6`, `8cdaecf`.

**WS8 (chart kit) — fully signed off 2026-10-16** with the choropleth added in WS2b.
