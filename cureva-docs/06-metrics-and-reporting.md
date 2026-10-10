# Metrics and Reporting

## Intelligence hierarchy

| Level | Questions answered | Examples |
|---|---|---|
| Operations | Are facilities reporting complete, current evidence? | Reporting rate, freshness, backlog, verified rows, missing service days |
| Care journey | Where are women losing continuity across pregnancy and after birth? | Booking timing, ANC contacts, ANC-to-delivery linkage, delivery-to-PNC linkage |
| Care quality | Which expected observations/interventions were recorded? | BP, Hb, HIV, syphilis, IPTp, tetanus, counselling coverage |
| Needs attention | Which documented conditions or pathways need follow-up? | Approved risk rules, open referrals, missed return dates, unresolved outcomes |
| Outcomes | What maternal and birth outcomes were documented? | Maternal outcome, live birth, stillbirth, birth weight, newborn referral, facility variation |
| Equity | Do service patterns differ by place or recorded age group? | Booking/contact completion/referral by facility, settlement, age band |

**Needs attention renders differently by role, on purpose.** A Facility
lead gets the case-level view — a worklist of named women, each with its
triggering rule and a "Mark actioned" step (`/needs-attention`, see
`09-ui-design-system.md` screen 12). An Organisation user never reaches
that page: they get the same lens rolled up into a single "Open
referrals" count on their Overview instead (screen 1). Same underlying
rules, two altitudes — one for the person who follows up, one for the
customer reading the numbers. See "Organisations and access scoping" in
`01-product-scope.md`.

## How the hierarchy and the lenses relate

These are two different tools, not two names for the same thing, and the
product needs both.

The **intelligence hierarchy** above is a classification of *altitude* —
six broad levels of question a dashboard can be asked at, from "is data
even coming in" (Operations) up to "who is being underserved" (Equity).
It exists to organize navigation and to make sure no level of question
gets skipped when the product is designed — it's a checklist for
completeness, not something you compute directly.

The **intelligence lenses** below are the concrete, buildable answer to
each of those levels: eleven specific, named analytical views, each one
mapped to exact fields on exact registers. Every lens sits under one or
more rungs of the hierarchy — for example, lens 1 (Perinatal & maternal
surveillance) is Outcomes plus Needs attention; lens 10 (Geographic
equity) is a slice of any lens above, and it *is* the Equity rung; lens
11 (Data-quality signal) is Operations. The hierarchy tells you what
altitude of question the product must be able to answer; the lens map
tells you, field by field, how Cureva Care actually answers it. When a new
metric or view is proposed, place it in the hierarchy first (which
question is it answering?), then check whether an existing lens already
covers it or a new lens is needed — never build a lens that doesn't map
to a rung, and never leave a rung with no lens under it.

## Intelligence lenses

This section is the answer to "what makes Cureva Care the go-to maternal
intelligence platform, specifically" (see "Vision — why this exists" in
`00-START-HERE.md`). It names eleven distinct analytical lenses the
product should support, and — because this matters for build discipline —
maps every single one back to the exact register fields it comes from.

**Rule for this section: nothing here uses a data source outside the
three registers this package already defines.** Every lens below is
built strictly from ANC, Delivery, and PNC fields as specified in
`03-templates-and-intake.md`, joined only through two structures this
package already has: the identity-linkage system (so a lens can follow
one woman across ANC → Delivery → PNC) and the facility/administrative
hierarchy (so a lens can be sliced by Ward, LGA, or State), both defined
in `02-data-model.md`. No lens below assumes a register, a form, or a
field that isn't already in the actual ANC, Delivery, and PNC registers
these facilities use — each lens is scoped to show exactly what those
fields support, nothing more.

One linkage rule applies throughout: a cross-register lens (one that
combines, say, an ANC risk factor with a Delivery outcome for the same
pregnancy) only populates for episodes that are actually linked — per
the identity-linkage rule in `02-data-model.md`, an unlinked encounter
still counts in every operational total, it just doesn't contribute to
the cross-register view until a strict match or a confirmed candidate
links it.

### Lens map

| # | Lens | Register(s) | Fields used | Status |
|---|---|---|---|---|
| 1 | Perinatal & maternal surveillance (MPDSR-style) | Delivery, PNC, ANC (linked context) | Delivery: `still_birth`, `baby_outcome`, `maternal_outcome`, `referral_status`, `birth_weight_kg`. PNC: `danger_signs`, `maternal_assessment`, `newborn_assessment`, `visit_outcome`, `referral_status`. ANC (linked): `blood_pressure`, `haemoglobin`, `genotype`, `blood_group_rhesus`, `hiv_result`, `syphilis_result` | Fully supported by current fields |
| 2 | High-risk pregnancy registry | ANC | `blood_pressure`, `haemoglobin`, `genotype`, `blood_group_rhesus`, `hiv_result`, `syphilis_result`, `gravida`, `parity` | Fully supported by current fields |
| 3 | HIV/syphilis testing coverage & retention (EMTCT-aligned) | ANC, PNC (via linkage) | ANC: `hiv_result`, `syphilis_result`. PNC: existence of any linked PNC contact for the same episode | Fully supported by current fields |
| 4 | Postnatal care coverage, timeliness & family planning | PNC | `visit_date`, `days_postpartum`, `family_planning` | Fully supported by current fields |
| 5 | Referral rate & closure | Delivery, PNC | `referral_status` (both registers) | Fully supported by current fields |
| 6 | Danger-sign detection-to-action | PNC | `danger_signs`, `visit_outcome`, `referral_status` | Fully supported by current fields |
| 7 | Facility delivery capability & outcome ratios (EmONC-style) | Delivery | `mode_of_delivery`, `attendant_category`, `delivery_place`, `maternal_outcome`, `baby_outcome`, `still_birth` | Fully supported by current fields |
| 8 | Newborn birth-weight & early feeding | Delivery, PNC | Delivery: `birth_weight_kg`, `baby_sex`, `still_birth`. PNC: `feeding_status`, `newborn_assessment` | Fully supported by current fields |
| 9 | Preventive intervention coverage (iron-folate, tetanus, IPTp) | ANC | `iron_folate_given`, `tetanus_given`, `iptp_given` | Fully supported by current fields |
| 10 | Geographic equity | Any lens above, sliced by facility | Facility's `ward_id` → LGA → State (see `02-data-model.md`) | Not a register field — every register row already carries a `facility_id`, so this is a slice of the lenses above, not a new source |
| 11 | Data-quality / register-keeping signal (RDQA-ready) | Intake pipeline metadata for all three registers | `extraction_confidence` (per field), `template_flags` (see `03-templates-and-intake.md`) | A meta-lens on how well each facility's actual paper registers extract against the template — not a clinical field, generated by the intake pipeline itself |

### What each lens answers

1. **Perinatal & maternal surveillance.** A Maternal and Perinatal Death
   Surveillance and Response (MPDSR)-style view: every stillbirth or
   severe maternal/newborn outcome becomes a traceable case, carrying its
   antenatal risk profile (BP, haemoglobin, genotype, HIV/syphilis status)
   alongside the delivery and postnatal record, because the identity
   linkage already ties one woman's ANC, Delivery, and PNC rows together.
2. **High-risk pregnancy registry.** Flags every ANC record with one or
   more recorded risk markers — raised blood pressure, anaemia,
   sickle-cell genotype (SS/SC), Rh-negative status, a positive HIV or
   syphilis result — so a facility or organisation can see its risk
   caseload, not just its total booking count.
3. **HIV/syphilis testing coverage & retention (EMTCT-aligned).** Testing
   coverage and positivity from ANC results, plus whether a
   positive-result woman has any linked PNC contact at all (retention in
   care) — the same coverage-and-retention framing donor programmes fund
   under elimination-of-mother-to-child-transmission (EMTCT) work. Testing
   and retention are exactly what the registers capture, and that's
   exactly what this lens reports — coverage and positivity, not a
   treatment cascade.
4. **Postnatal care coverage, timeliness & family planning.** Three
   related reads on the same PNC records: whether a birth got any PNC
   contact at all, whether that first contact happened early (using
   `days_postpartum` — the postnatal-care-within-48-hours window is one of
   the most widely tracked postnatal indicators globally), and, for
   contacts that occurred, postpartum family-planning method and timing —
   a direct read on birth-spacing and repeat-pregnancy prevention.
5. **Referral rate & closure.** How often a referral is recorded — by
   facility and register family — and what share of those referrals show
   a documented outcome, using the `referral_status` already captured on
   Delivery and PNC. This is the same signal the "Referral closure"
   metric in the MVP metric set tracks, surfaced here as its own lens.
6. **Danger-sign detection-to-action.** Of every danger sign recorded in
   PNC, what fraction led to a referral or documented action versus
   sitting unresolved in the record — an accountability lens as much as
   a clinical one.
7. **Facility delivery capability & outcome ratios.** Mode of delivery,
   attendant category, and delivery place, compared facility to facility —
   an EmONC-style signal on service-delivery capability and access (e.g.
   an unusually high or low caesarean rate, or a low
   skilled-birth-attendance rate). The same fields also support the two
   outcome ratios EmONC programmes report on: an institutional maternal
   mortality ratio and a case-fatality read, both computed from
   `maternal_outcome` against total deliveries at that facility.
8. **Newborn birth-weight & early feeding.** Low-birth-weight rate and
   early breastfeeding practice, useful on its own and as an input to any
   nutrition-programme partnership.
9. **Preventive intervention coverage.** Coverage of the three preventive
   ANC interventions the register captures — iron and folate
   supplementation, tetanus vaccination, and IPTp (malaria prevention in
   pregnancy) — by facility. This is one of the most consistently
   donor-funded indicator families in maternal health programmes (malaria
   prevention in particular, given Nigeria's PMI/Global Fund priority-
   country status), and it was sitting in the ANC register unused until
   this lens.
10. **Geographic equity.** Any lens above, sliced by Ward, LGA, or State —
    usually the single most actionable view for an Organisation user
    deciding where to send resources, and it exists because the facility
    hierarchy was built as a first-class part of the data model, not
    bolted on later.
11. **Data-quality / register-keeping signal (RDQA-ready).** Which
    facilities' physical register-keeping habits deviate most from the
    template (lowest average extraction confidence, most template flags) —
    a genuine, unique-to-this-architecture signal for where to send
    retraining or fix a template, generated as a side effect of the
    intake pipeline itself. This is also what a Systems admin or
    an NGO's own team would otherwise pay a consultant to produce
    manually: most international donors (e.g. PEPFAR, Global Fund)
    require a periodic Routine Data Quality Assessment (RDQA) as a grant
    condition, and this lens is that assessment, generated continuously
    rather than as a one-off site visit.

## MVP metric set

| Metric | Numerator | Denominator / boundary |
|---|---|---|
| Early ANC booking | Episodes booked in the approved early-gestation window | Episodes with recorded booking gestational age |
| ANC contact distribution | Episodes by highest recorded contact number | Linked pregnancy episodes in the selected period |
| Eight-contact completion | Episodes with ≥8 recorded contacts | Episodes eligible under the configured clinical rule — never all visits |
| Screening coverage | Episodes/contacts with a recorded test | Eligible records with necessary context; completeness shown separately |
| Intervention coverage | Eligible episodes with a recorded intervention | Eligibility/timing defined in a versioned clinical rule |
| Referral closure | Referrals with a documented outcome | All referrals created in the period |
| Delivery linkage | Birth events linked to an ANC episode | Birth events in participating facilities |
| Postnatal linkage | Birth episodes with a recorded PNC contact | Birth episodes with sufficient identifiers for linkage |
| Outcome distribution | Count by documented maternal/newborn outcome | Records with a documented outcome — never infer missing ones |

Standards baseline: WHO's eight-antenatal-contact model and its
software-neutral Digital Adaptation Kits for ANC/PNC. Use as a starting
point, then version any country/programme adaptation — never hard-code a
clinical threshold without local clinical sign-off.

## Risk and follow-up rules

- Rules operate only on recorded values. A blank is unknown, not normal
  (non-negotiable rule #6).
- Each rule stores its clinical owner, version, effective date, source
  guidance, and severity.
- The UI shows why a record appears in a worklist and the exact source
  fields used — no black-box flags.
- Rules create operational prompts for review/follow-up. They never create
  diagnoses or treatment instructions.
- MVP examples for clinical configuration: recorded abnormal blood
  pressure, anaemia result, danger signs, overdue return date, open
  referral, missing postnatal follow-up.
- **A Facility lead can mark a worklist item as followed up on**
  (`POST /api/v1/worklists/{itemId}/action`, stored in
  `worklist_actions` — see "Worklist actions" in `02-data-model.md`).
  This is an audit overlay, not a resolution: it never edits the
  underlying register data or `referral_status`, and the item can
  resurface on a later worklist if the rule still evaluates true — the
  UI shows the action history on it either way. Settled 2026-09-21: the
  worklist was view-only through the prototype review stage; this was
  added because nothing in the app otherwise recorded that a Facility
  lead had actually done something about a flagged item.

## Healthcare-facing report

Written for facility and organisation action, not register administration. Deterministic
metrics and charts are generated first; an optional LLM call may turn
already-computed aggregate metrics into prose — no identifiable row is ever
sent to it, and it cannot invent causes, impact, or prevalence.

Report sections:

- Executive interpretation and the most material change in the period.
- Reporting coverage, evidence freshness, limitations.
- ANC access and continuity, including booking and contact patterns.
- Screening, intervention, risk, and referral patterns, with denominators.
- Delivery, maternal, and newborn outcomes as documented.
- Facility variation and data-quality issues affecting interpretation.
- Three ranked actions, each with an owner, rationale, and suggested
  follow-up measure.

Minimum required charts: contact activity over time; booking
gestational-age distribution; care-journey funnel; screening/intervention
coverage; referral/outcome distribution by facility.

## Data-quality sanity checks (MVP addition)

Beyond presence/completeness, flag physiologically implausible values at
intake time (see `plausible_range` in the template schema,
`03-templates-and-intake.md`) — e.g. blood pressure outside a sane
systolic/diastolic range, birth weight outside 0.5–6.0kg. These publish as
flagged rows (visible in the Records view with a warning indicator), not as
silently accepted or silently blocked data — a human decides what to do
with them.

## Stale-facility alerting

A facility that goes without a new intake for the configured threshold
(`stale_facility_alert_days` in `platform_settings`, default **14 days**)
triggers a notification to that facility's Facility lead (and any
organisation with a grant covering that facility), rather than relying on
someone noticing it on the Facilities dashboard. Implemented as a
scheduled job (see `04-architecture-and-stack.md`) checking
`GET /api/v1/facilities/{id}/status` for every active facility.

Both the threshold and the notification channel are configuration, not
code:

- The **14-day window is a `platform_settings` value**, editable by a
  Systems admin from `/admin/settings` — set it to 10 days, back
  to 14, or anything else, with no code change and no redeploy. See
  "Platform configuration and notification preferences" in
  `02-data-model.md`.
- The **channel is per recipient, not fixed for everyone.** The job
  resolves who should be notified (by role and facility scope),
  then sends each recipient's alert on exactly the channel(s) recorded in
  their own `notification_preferences` row for the `stale_facility_alert`
  type — email, SMS, both (the shipped default), or none. A recipient who
  prefers SMS-only never gets an email for this alert, and vice versa;
  nothing in the alert job assumes a channel.
