# 12 — Intelligence Expansion (Tier 1 & 2): the world-class modules

**Status: APPROVED (product owner, 2026-10-29).** Authoritative build plan:
implemented module by module, each committed + pushed on its own, verified live,
and **signed off** in the checklist at the end.

**Approved answers to the open questions:**
1. Coverage denominators — seed from WorldPop + national projections, labelled
   "estimate", admin-adjustable later. ✅
2. Death reviews — **Facility lead** captures them for now (Option A); the model
   is built so a separate **Reviewer** role can be switched on later without
   rework. ✅
3. New capture (reviews, referral outcomes) — **optional**; a facility that
   doesn't capture simply shows "not recorded". ✅
4. Plan placement — as proposed (Professional: Coverage, Equity, Quality, Goals;
   Enterprise: MPDSR, Referrals, Early Warning). ✅

This extends `11-intelligence-module.md` (the descriptive intelligence already
shipped) toward **coverage, accountability, and prediction** — the leap from
"what happened" to "are we reaching everyone, are deaths being prevented, and
what is about to happen." Goal: the best maternal-health data-intelligence
platform in Africa.

---

## 0. Preliminary — reframe the data-quality page (quick, do first)

**Decision taken:** we do not show buyers how confident our AI is at reading
handwriting. That is internal engineering QA and reads like a confession.

- **Remove from the customer view** (move to admin-only): "AI reading
  confidence" / extraction confidence and the "how clearly registers are being
  read" trend.
- **Keep and reframe** the facility-level reliability — completeness,
  timeliness, implausible values, open column issues — as a tool *for the buyer*:
  *which facilities report completely and on time, and which need support.*
- **Rename:** "Data quality (RDQA)" → **"Reporting reliability"** (sidebar, page
  title). Subtitle: *"Which facilities report completely and on time."*

Same underlying data; opposite message — from "here's how we struggle" to
"here's a tool to manage your network."

---

## Principles carried forward (from doc 11) + two new ones

All eight principles in doc 11 still apply (only the three registers; always a
denominator; never infer a blank; AI touches aggregates only; explainable not
black-box; access-scoped; service dates). Two additions for this phase:

9. **Estimates are labelled as estimates.** Coverage denominators come from
   external population data (census / WorldPop / official projections). Every
   coverage figure names its denominator source and year, and is visibly marked
   an estimate. We never pass an estimate off as a count.
10. **Prediction is honest and explainable.** Forecasts start simple and
    transparent (trend + seasonality, confidence range shown), never a black
    box. Every prediction shows what drove it and can be wrong gracefully — it
    is a prompt to look, not a verdict.

---

## The modules (Tier 1 & 2)

Each module below is a gateable entry in the plan/entitlements system we already
built (doc: plans & modules). "Plan placement" says which subscription tier it
ships in by default (admin can still move it).

### Tier 1 — highest leverage

#### M1 · Coverage & Reach — "are we reaching everyone?"
- **What:** turn activity counts into **coverage rates** against the expected
  number of pregnant women per ward/LGA/state. "We did 820 first ANC visits" →
  "we reached an estimated 61% of expected pregnancies in Nassarawa LGA."
- **Buyer value:** the headline maternal-health question for every government and
  donor. Shows reach, gaps, and underserved areas on the map.
- **Data needed:** a new **population-denominator reference table** (expected
  pregnancies per area per year), seeded from census/WorldPop/official
  projections. *No new burden on facilities.*
- **We build:** denominator reference model + admin screen to load/adjust it;
  coverage metrics (ANC1, ANC4+, skilled birth attendance, PNC) as rate =
  recorded / expected; coverage choropleth map + league table reusing the
  existing geo rollup; prominent "estimate · source · year" labelling.
- **Plan placement:** Professional.
- **Caveats:** denominator quality varies; always labelled an estimate; where no
  denominator exists we fall back to counts, never a fake rate.

#### M2 · Death Reviews & Response (MPDSR)
- **What:** the WHO-standard loop on top of the deaths we already detect — every
  maternal/newborn death gets a structured review: cause, **was it avoidable?**,
  contributing factors, and a follow-up action with an owner and status.
- **Buyer value:** governments are *required* to run MPDSR and mostly do it on
  paper. Owning this workflow makes us indispensable to a Ministry of Health; it
  is the clearest "we are serious infrastructure" signal.
- **Data needed:** a new **death-review workflow** (new capture by facility
  leads / designated reviewers) linked to the existing surveillance death record.
- **We build:** DeathReview model (cause category, avoidability, factors,
  actions, status) + review form + a review queue ("deaths awaiting review") +
  an aggregate "avoidable factors" dashboard (what keeps killing mothers, and
  whether actions close). Case detail stays access-scoped — organisations see
  aggregates only, never the woman-level review.
- **Plan placement:** Enterprise.
- **Caveats:** avoidability is a clinical judgement recorded by a reviewer, not
  inferred by us; we store and summarise it, we don't decide it.

#### M3 · Early Warning — "what's about to happen"
- **What:** move selected signals from reactive to anticipatory: forecast which
  facilities will miss ANC/coverage targets, flag likely severe-outcome clusters
  before they spike, and surface women likely to drop out of care.
- **Buyer value:** prediction is the clearest "world-class" differentiator; it
  lets a program act *before* harm, not after.
- **Data needed:** none new — uses accumulated history (needs a few months of
  data per facility to be meaningful).
- **We build:** a transparent forecasting layer (trend + seasonality with a
  shown confidence band) feeding a single "Watch list — likely to need attention
  soon" view; each item states the fields and trend that triggered it.
- **Plan placement:** Enterprise.
- **Caveats:** honest and explainable only (principle 10); shown as a prompt to
  look, with a confidence range, never a certainty.

### Tier 2 — depth buyers pay more for

#### M4 · Quality of Care
- **What:** not just *did* she attend, but did she get the *right* care — BP +
  urine + blood tests each ANC visit, correct management at delivery, danger-sign
  screening — measured against WHO standards.
- **Buyer value:** depth; proves the care delivered actually meets standards, not
  just that a visit occurred.
- **Data needed:** the clinical fields our templates already extract (BP, tests,
  interventions); a few template fields may need adding where a register has them
  but we don't yet capture them.
- **We build:** a care-quality scorecard per facility/region (standards met vs
  missed), reusing the metric-meter components; gaps ranked into actions.
- **Plan placement:** Professional.
- **Caveats:** measures what's recorded; a blank is "not recorded," never "not
  done" — stated plainly.

#### M5 · Referral Pathways & Outcomes
- **What:** close the loop on the referrals we already flag — did she **arrive**
  at the referral facility, and what happened? Map the pathways and the
  bottlenecks between PHC and hospital.
- **Buyer value:** referral breakdowns are where mothers die; completing the loop
  is high-value and currently invisible on paper.
- **Data needed:** **referral outcome capture** (arrived / not / outcome) — a new
  field + light workflow linking the sending and receiving facility.
- **We build:** referral-outcome capture; a pathway/bottleneck view (sent vs
  arrived vs completed, time-to-arrival); "referrals that went nowhere" worklist.
- **Plan placement:** Enterprise.
- **Caveats:** cross-facility linking respects access scope; needs both ends to
  record.

#### M6 · Equity — "who is being left behind"
- **What:** break every headline metric by sub-group — rural vs urban, poorest
  wards, first-time vs grand-multipara, age bands — to expose systematic gaps.
- **Buyer value:** donors fund *equity*; "these 12 wards are systematically
  underserved" is directly sellable.
- **Data needed:** mostly existing (parity/age already captured, geography
  present); an optional area-deprivation/urban-rural layer sharpens it.
- **We build:** an equity lens (reusing parity-equity patterns already shipped)
  across coverage and quality, with an "equity gap" ranking.
- **Plan placement:** Professional.
- **Caveats:** small sub-groups flagged as small samples; never guess missing
  sub-group data.

#### M7 · Goals & Targets (SDG / national)
- **What:** track progress against SDG 3.1 (MMR < 70), ANC4+, skilled-birth-
  attendance and national targets, with a clear "on track / off track" read.
- **Buyer value:** governments and donors report against these constantly; doing
  it for them is low effort, high stickiness.
- **Data needed:** none new — configurable targets + existing metrics.
- **We build:** an admin-set targets table + a "progress to targets" scorecard
  with trend-to-goal.
- **Plan placement:** Professional.
- **Caveats:** targets are configuration, not clinical claims.

---

## Build sequence (the order I'll work, and check in with you at each)

Led by your preference (Coverage first, then MPDSR), ordered so data-dependent
pieces land in a sensible order:

0. **RDQA reframe** (preliminary, quick).
1. **M1 Coverage & Reach** — denominator reference + coverage rates + map.
2. **M7 Goals & Targets** — small, and it makes coverage immediately meaningful
   against goals (quick win sequenced early).
3. **M6 Equity** — builds directly on coverage + existing patterns.
4. **M4 Quality of Care** — standards scorecard from existing clinical fields.
5. **M5 Referral Pathways & Outcomes** — adds referral-outcome capture.
6. **M2 Death Reviews (MPDSR)** — the review workflow + aggregates.
7. **M3 Early Warning** — last, because it builds on all the above + history.

Each module: backend + frontend, committed and pushed on its own, verified live
(screens/tests), then I report back before moving on — so you can steer "until
we're done."

---

## How it fits what we already built

- **Plans & modules:** each module is a new gateable key in the catalogue
  (`coverage`, `death_reviews`, `early_warning`, `quality_of_care`,
  `referrals`, `equity`, `targets`). Admin ticks them into Essentials /
  Professional / Enterprise exactly as today; nothing hard-coded.
- **Access scope:** every new view, list and export respects role +
  organisation grant scope and the totals-only / no-names / full-detail levels.
  Case-level data (reviews, referral cases) never reaches an organisation user.
- **Hierarchy:** all new geo views reuse the facility → ward → LGA → state
  rollup already in place.
- **Plain language:** every new surface ships in the same plain, non-technical
  language we standardised — no jargon on customer screens.

---

## Open questions for you (so I don't guess)

1. **Coverage denominators:** OK to seed from public estimates (WorldPop /
   national projections) with clear "estimate" labelling for now, and let admins
   adjust per area later? (Alternative: wait for official ministry figures.)
2. **MPDSR reviewers:** should death reviews be done by the Facility lead, or do
   you want a separate "Reviewer" role? (Affects the workflow + permissions.)
3. **New data capture (M2, M5):** fine for facilities to log a little more (death
   review form; referral arrived/outcome), or should these stay optional so a
   facility that doesn't capture them simply sees "not recorded"?
4. **Default plan placement:** I proposed Professional vs Enterprise above —
   happy with that split, or move any module?

---

## Sign-off checklist (filled as each ships)

- [x] 0 · RDQA reframe — shipped 2026-10-29 (commit fc36c8d)
- [x] M1 · Coverage & Reach — shipped 2026-10-29 (commit 9a2b564)
- [x] M7 · Goals & Targets — shipped 2026-10-29
- [ ] M6 · Equity
- [ ] M4 · Quality of Care
- [ ] M5 · Referral Pathways & Outcomes
- [ ] M2 · Death Reviews (MPDSR)
- [ ] M3 · Early Warning
