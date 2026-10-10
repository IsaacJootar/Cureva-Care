# Product Scope

## Objective

Cureva Care makes maternal-care activity, continuity, risk documentation,
referrals, and outcomes visible across facilities and time. It answers:
what care was recorded, where continuity is breaking, which facilities
need attention, and what evidence supports each conclusion.

The underlying ambition is bigger than compliance tracking: Cureva Care is
meant to become the go-to maternal intelligence platform — where
register data turns into trend analysis and neonatal/perinatal
surveillance an organisation can actually act on. See "Vision — why
this exists" in `00-START-HERE.md`.

## Product principles

- **Register faithful.** Preserve the source exactly as written. Normalize
  only when the transformation is deterministic, and always retain the raw
  value alongside the normalized one.
- **Batch based and append only.** Every uploaded file is a distinct
  intake. Repeated serial/card numbers across batches never replace older
  records.
- **Verified only.** Unverified rows stay outside analytics, reports, and
  any export presented as evidence.
- **Service date first.** Filters and trends use the date of care, never
  the date of upload, scan, or publication.
- **Transparent intelligence.** Every metric shows its denominator, a
  data-completeness measure, and a route back to the source evidence.
- **Clinical governance before automation.** Risk and follow-up rules are
  versioned, configurable, and approved by a named clinical owner.
- **Useful before clever.** Deterministic metrics and worklists ship
  before any predictive or generative feature.
- **Configuration over hard-coding.** Any operational value someone could
  reasonably want to tune — an alert threshold, a confidence cutoff, which
  channel a notification goes out on — lives in the platform configuration
  module (see "Platform configuration and notification preferences" in
  `02-data-model.md`), editable by the right role without a code change.
  It is never a constant buried in application code, and it is never set
  in more than one place.

## MVP scope

| In the MVP | Outside the MVP |
|---|---|
| Batch intake with source-file retention | Full electronic medical record |
| ANC booking and contact records | Prescribing or autonomous clinical recommendations |
| Delivery and birth outcome records | Patient-facing mobile app or messaging automation |
| Postnatal mother and newborn contacts | Claims, billing, inventory, or pharmacy management |
| Referrals, follow-up gaps, documented outcomes | Predictive risk scores or population prevalence claims |
| Facility/date/pregnancy filters | Unreviewed data appearing in any dashboard |
| Evidence explorer, exports, analytical briefs | National interoperability certification at pilot launch |
| Strict-identifier fast path AND human-confirmed probabilistic candidate matching for identity linkage | Auto-merging any match without human confirmation |
| Per-facility templates, falling back to a shared default | Assuming every facility uses one identical layout |
| Register-family cross-check: hold and ask when a photographed page looks like a different register than declared | Silently publishing under whichever family the officer happened to tap |
| Admin-approved official templates; a data officer can flag a mismatch | Facilities self-publishing their own official template |
| Magic-link authentication AND common SSO providers | Rolling custom authentication from scratch |
| Stale-facility alerting (configurable threshold, default 14 days; each recipient's channel configurable) | — |
| The full risk/referral rule engine and healthcare-facing report generator | — |
| Photographed-register intake (capture or upload) with AI/OCR field extraction | AI auto-verifying or auto-publishing any extracted row; CSV/Excel upload as an intake path |

## Release strategy

**There is one intake channel: a photographed register page.** There is
no CSV or Excel upload anywhere in this product — a data officer captures
a photo with their device's camera or uploads an existing photo (taken on
any device), and AI/OCR reads that image and extracts the register's
fields. Whether the photo was just taken or was taken earlier on another
device and transferred over makes no difference — either way it reaches
the system as an image file. The UI presents this as two entry points to
the same channel: **Capture Register** and **Upload Register** — see
"Who submits data, and for which facility" below for how a data officer
picks the facility a given batch belongs to before either action.

Every image-sourced row carries a per-field confidence score. A
high-confidence field is accepted without forcing a click; anything below
the confidence threshold is visibly flagged and a human reviewer must
confirm or correct it before that row can publish — see
`03-templates-and-intake.md` for the full extraction and confirmation
flow. The AI never verifies or publishes its own extraction; it only
proposes. If the extracted data doesn't match the resolved template at
all (columns/fields the template doesn't recognize), the existing
template-mismatch workflow applies unchanged: the data officer can flag
it, and only a Systems admin can turn that into an official new
or updated template — see "Facility flagging vs. admin approval" in
`03-templates-and-intake.md`.

## Roles

Four roles, and every one of them is either producing data, making
sense of it for one facility, consuming it as a customer, or configuring
the system that everyone else runs on. Nothing overlaps.

| Role | Primary job | Access |
|---|---|---|
| Data officer | Cureva Care's own staff. Submits register batches — capturing or uploading a photo — choosing which facility each batch belongs to. | Scoped to the intake pipeline only: their own submitted batches, nothing else. Not facility-locked — see below. |
| Facility lead | The clinical reviewer at one facility. Reviews pregnancy timelines, risks, referrals, follow-up gaps, confirms candidate identity matches. Every facility has one. | Identifiable access, locked to their one facility. |
| Organisation user | Anyone at a customer organisation (an NGO, a government body, a business — any buyer of Cureva Care's intelligence). Consumes dashboards and reports. | View-only, locked to their organisation's granted facilities/regions, at the tier a Systems admin set. Never captures, corrects, or uploads anything. |
| Systems admin | The final configuration authority. Creates facilities, approves templates, creates organisation accounts and sets their facility/region grants, creates users. | Administrative access only — no default access to dashboards or PHI just for holding this role. |

**Who submits data, and for which facility.** Data officers are Cureva Care's
own internal staff, not hospital employees — they are not assigned to
one facility the way a Facility lead is. Instead, a Data officer works
inside a **session-level workspace switcher**: they search a flat
facility index by name, LGA, or state, select one, and their entire
screen — the intake card, the stat tiles, the intake history — scopes to
that facility until they switch again. This is a different, faster
control than the hierarchical State → LGA → Ward picker used for
one-off setup tasks (`/admin/facilities`, granting an organisation
access) — a Data officer does this switch many times a day, so it's a
single search field, not a multi-step drill-down. See "Workspace
switcher (Data officer)" in `09-ui-design-system.md`'s Component
library for the exact interaction. One data officer might submit a
Delivery register for a facility in Kano in the morning and an ANC
register for a facility in Lagos in the afternoon — nothing in their
account restricts which facility they can submit for. See "Who submits
data, and for which facility" in `03-templates-and-intake.md` for
exactly how this works in the intake flow.

**A Data officer's access stops at the intake pipeline.** They see their
own submission history and status, confirm/correct fields on their own
submitted batches, and flag template mismatches — nothing else. They do
not get `/overview`, `/care-journey`, `/records`, or `/reports`: those are
for the people making sense of a facility's data (Facility lead) or
consuming it as a customer (Organisation user), and a Data officer isn't
either of those.

**Every facility has exactly one Facility lead**, and their view of
`/overview`, `/care-journey`, `/needs-attention`, `/outcomes`, `/records`,
and `/reports` is always locked to that one facility — no facility
switcher, no cross-facility comparison, because there's nothing to
switch between. See "Facility-level dashboards" below.

**All roles are centrally managed — no self-service for account
creation.** Only a Systems admin creates a user account and assigns it a
role — nobody signs themselves up, and a Facility lead never picks their
own facility (a Systems admin assigns it). This is invite-only end to
end (see `07-security-privacy-access.md`), and it's what makes "locked
to their one facility" an enforceable rule rather than a convention —
the assignment lives in the system, set by a Systems admin, not asserted
by the user. The one partial exception: an Organisation user flagged
`can_manage_org_users` (see `02-data-model.md`) can invite *more* users
into their own organisation — but only within the facility/region scope
a Systems admin already granted that organisation; they can never widen
their own organisation's access.

## Organisations and access scoping

**Cureva Care is sold as a SaaS product to more than just NGOs** — government
bodies, donor agencies, and other businesses that need maternal
intelligence are all real customers, and the product is not designed
around one fixed buyer type. Every one of them becomes an
**organisation** account, and every organisation account works the same
way, whoever it belongs to:

- **One shared Cureva Care deployment, not one per customer.** This is what
  "multi-tenant" means here: a single application and database serve
  every organisation. What keeps them apart isn't separate
  infrastructure, it's that every organisation-scoped query is filtered,
  server-side, to exactly that organisation's granted facilities — the
  same enforcement pattern already used to lock a Facility lead to their
  one assigned facility, just applied to a configurable *set* of
  facilities instead of exactly one.
- **Organisations never capture, correct, or upload data. They are
  strictly view-only.** An organisation has no data officers and no
  facility leads of its own, and no path into the intake, template,
  identity-review, or settings screens at all — not hidden-but-reachable,
  genuinely absent, and rejected server-side if ever attempted.
  Facilities are operated by Data officers and Facility leads exactly as
  described above; organisations only ever consume what that operation
  produces.
- **Access is configured per organisation, by a Systems admin only —
  never self-service.** When an organisation account is created
  (`/admin/organisations`, see `05-api-routes.md`), the Systems admin
  grants it access to a specific set of facilities, or to whole regions
  (a State, an LGA, or a Ward — which then covers every facility under
  that node, including ones added later), and sets the access tier for
  that grant: aggregate, de-identified, or identifiable (the same three
  tiers as `07-security-privacy-access.md`). An organisation might be
  granted 2 facilities, or 50, across however many regions its
  subscription covers — expressed as rows in
  `organisation_facility_access` (see `02-data-model.md`).
- **Within an organisation, one person can manage the rest.** An
  Organisation user flagged `can_manage_org_users` can invite and manage
  that organisation's own colleagues (also Organisation users) — but
  cannot change which facilities, regions, or access tier their
  organisation was granted. That's the same boundary a Facility lead
  already has over their own facility assignment: you can't grant
  yourself more scope than a Systems admin gave you.
- **Organisation users reuse the existing dashboards, not a separate
  build — with one deliberate exception.** `/overview`, `/care-journey`,
  `/outcomes`, `/facilities`, `/records`, and `/reports` are the same
  pages — an organisation user gets the same view a Facility lead gets,
  just scoped to a configurable set of facilities instead of exactly
  one. **Needs attention (`/needs-attention`) is Facility-lead-only.**
  Organisations buy Cureva Care's intelligence, not its worklist: the
  case-level "who needs follow-up and why" view belongs to the person
  who can actually act on it, not the customer reading the numbers
  afterward. An organisation still sees this signal, rolled up —
  an "Open referrals" count on their Overview (screen 1 in
  `09-ui-design-system.md`) — never the named-case list. See "Needs
  attention" in `06-metrics-and-reporting.md` for how the same
  underlying lens serves both views.
- **If Cureva Care's own team ever wants a cross-facility view of the whole
  platform**, the mechanism already exists and nothing new needs
  building for it: set Cureva Care's own team up as an organisation, granted
  access to every facility. A Systems admin's job is configuration, not
  browsing data — anyone who needs to browse data becomes an
  Organisation user, whether they work for Cureva Care or for a customer.

## Facility-level dashboards

A Facility lead shares the same Next.js app and design system as
everyone else, but what renders is narrowed to their one assigned
facility — this is a locked scope, not just a default filter a user
could widen. They don't see the ADMIN section of the sidebar (Templates,
Manage facilities, Organisations, Users & roles) at all, and they don't
see a facility switcher, since there is nothing to switch between.

- **Facility lead's landing view** is the clinical counterpart to a Data
  officer's intake work: their facility's own care-journey funnel,
  their open referrals and overdue follow-ups, and their identity-review
  queue (confirming or rejecting candidate matches — a Facility lead is
  the only role that does this). They also have pregnancy-timeline and
  records access, scoped to their own facility's women only.
- Every shared route (`/overview`, `/care-journey`, `/outcomes`,
  `/facilities`, `/records`, `/reports`) exists for a Facility lead —
  it's the same page, not a separate build — but the facility filter on
  it is pre-set and locked to their assigned facility, and any
  cross-facility comparison view is hidden rather than shown empty.
  Organisation users see the same pages too, scoped instead to their
  organisation's granted facilities — one facility for a Facility lead,
  a configurable set for an Organisation user, same mechanism either
  way. **Needs attention (`/needs-attention`) is the one exception**: a
  Facility lead gets it, locked to their facility; an Organisation user
  never gets the route at all (see "Organisations and access scoping"
  above).
- A Data officer doesn't get these pages at all — see "Roles" above.

## Intake-to-intelligence workflow

1. A data officer chooses which facility this batch is for (see "Who
   submits data, and for which facility" above), then receives one
   facility register batch: register family, service period, and one or
   more images of the register page (captured live or uploaded).
2. Fingerprint the image file(s) (checksum). Retain the original source.
   Reject an exact duplicate without creating new rows.
3. Resolve the correct template for this facility and register family
   (facility-specific if one exists, otherwise the shared default), then
   run AI/OCR extraction against it, field by field, with a confidence
   score per field. Validate structure, types, and required identifiers.
4. Cross-check the extracted fields against all three register families'
   signatures (see "Register-family cross-check" in
   `03-templates-and-intake.md`). If the page looks like a different
   family than declared, hold the intake and ask the data officer to
   confirm or switch before anything moves on to field confirmation.
5. Store raw (the original extraction) and normalized values with
   field-level provenance. Never overwrite an earlier batch.
6. Hold every row as "awaiting confirmation" until every field below the
   confidence threshold has been confirmed or corrected by a human
   reviewer — only then can the row publish. High-confidence fields don't
   block this; only flagged ones do.
7. Attempt identity resolution for each row (strict identifier, then
   human-confirmed candidate matching).
8. Project verified rows into the maternal model, calculate deterministic
   metrics, refresh facility aggregates.
9. Expose the new evidence in dashboards, pregnancy timelines, exports, and
   saved reports — to the facility's Facility lead, and to any
   organisation granted access to that facility.

Flow: `facility chosen → register photo → AI/OCR extraction →
register-family cross-check → field-level lineage → confirmation gate →
identity resolution → maternal projection → intelligence → report`

## Publication modes

| Mode | Behaviour | Use |
|---|---|---|
| Awaiting confirmation | Every row lands here after extraction; store pending rows and per-field confidence/flags; excluded from intelligence until every flagged field is confirmed | The standard path for every intake — there is one intake channel |
| Rejected | Retain intake metadata and reason; publish no rows | Wrong facility, unreadable/corrupted image, unsupported register, duplicate checksum |
