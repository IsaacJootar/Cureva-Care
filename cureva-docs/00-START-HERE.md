# Cureva Care Maternal Care Intelligence — Build Package (Final)

## What this is

This is the complete handoff package for building Cureva Care: an intelligence
and reporting layer for maternal-care registers (ANC, Delivery, PNC). It is
derived from the original product PRD and a full design/alignment
discussion with the product owner, and is now locked for build.

**Cureva Care is not an electronic medical record.** It ingests reviewed batches
of maternal register data, verifies them, and turns them into dashboards,
worklists, and reports for facility leads and the organisations that pay
to consume them. It never diagnoses, prescribes, or recommends treatment.

## Vision — why this exists

Getting registers into a clean, verified, identity-linked database is the
foundation, not the point. The point is what gets built on top of it:
**Cureva Care's ambition is to become the go-to maternal intelligence
platform** — the place anyone running or funding maternal-health work
goes to actually make sense of ANC, Delivery, and PNC data. That means
real trend analysis over time, neonatal and perinatal surveillance
across facilities, and turning raw register entries into evidence
someone can act on — not just a system that confirms whether a facility
submitted its paperwork.

This is why the design in this package goes well past "store the data
correctly": the metrics hierarchy (`06-metrics-and-reporting.md`), the
care-journey/outcomes/needs-attention views (`01-product-scope.md`), the
per-facility comparison, and the healthcare-facing report generator all
exist in direct service of this ambition. When a design decision or a
future feature is ambiguous, favor whichever choice makes the platform
better at surfacing real maternal and newborn intelligence — that is the
product's actual north star, not register digitization for its own sake.

## How to use this package

Read in order — each file builds on the ones before it.

1. `01-product-scope.md` — what we're building, for whom, in/out of scope.
2. `02-data-model.md` — the database entities and how they relate.
3. `03-templates-and-intake.md` — how batches get validated, matched to the
   right register format, and published.
4. `04-architecture-and-stack.md` — the technical stack and service
   boundaries.
5. `05-api-routes.md` — the API surface between backend and frontend.
6. `06-metrics-and-reporting.md` — dashboards, metrics, generated reports.
7. `07-security-privacy-access.md` — access tiers and required controls.
8. `08-delivery-plan.md` — the build plan, team, and launch gates.
9. `09-ui-design-system.md` — the exact look and feel: navigation,
   design tokens (light and dark mode), components, and every screen.
10. `10-build-execution-checklist.md` — the section-by-section checklist
    and git workflow a coding agent follows while building this, and how
    it marks its own progress.

## Non-negotiable rules

These rules govern almost every design decision in this package. If a
future change conflicts with one of these, stop and reconsider — don't
quietly override it.

1. **Never touch the original data.** Raw uploaded values are preserved
   forever, untouched. Cleaned/normalized values live alongside them, never
   in place of them.
2. **New file in = new batch, never a replacement.** Nothing is ever
   silently overwritten. A duplicate file upload is a no-op (detected by
   checksum), not a re-import.
3. **Unverified data doesn't count.** Rows that haven't been reviewed and
   published are invisible to every dashboard, report, and export.
4. **Service date, not upload date, drives everything.** Every filter and
   trend uses the date care was given (`service_date`), never
   `received_at` or `published_at`.
5. **Every number needs a denominator.** No percentage is ever displayed
   without its underlying count and a completeness indicator.
6. **Blank means unknown, not normal.** Risk rules and coverage metrics
   must treat missing fields as missing, never as a negative/clear result.
7. **Organisation accounts are view-only, always.** An organisation (an
   NGO, a government body, a business, or any buyer of Cureva Care's
   intelligence) never captures, corrects, or uploads register data,
   never has its own data officers or facility leads, and only ever sees
   the specific facilities or regions a Systems admin has
   explicitly granted it — enforced server-side, not just hidden in the
   UI. See "Organisations and access scoping" in `01-product-scope.md`.

## Scope philosophy

Scope in this package is set by what the product needs to be correct and
safe — not by what a small human team could finish in a few weeks. This is
being built by an AI coding agent (Claude Code), so nothing is deferred or
cut purely for time. Where the original PRD described something fully, it
is built fully here.

## Final locked decisions

- **Backend:** Python + Django, exposing a REST API (Django REST
  Framework). Django owns all data processing, validation, rules, jobs,
  and the database connection. It renders no user-facing pages itself —
  not even its own built-in admin panel is used as part of the product.
- **Database:** PostgreSQL, for transactional guarantees around the
  append-only publish step and strong JSON support for template/lineage
  data.
- **Frontend:** One Next.js (React) application, styled with Tailwind CSS,
  is the single UI for the entire product — every dashboard, every
  internal admin screen (facility management, template management, user
  management), login, everything. There is no second, differently-styled
  "internal tools" interface anywhere in the product.
- **Background jobs:** a database-backed task queue (e.g. `django-q2`)
  rather than introducing Redis/Celery — keeps the number of moving parts
  down unless real throughput later proves it's needed.
- **Identity linkage:** two paths, both built. A record with a stable
  identifier (facility card/folder number or equivalent facility-issued ID)
  links automatically. A record without one gets a best-effort candidate
  match against existing women — comparing name, age/date of birth, phone
  number, and facility — shown with a confidence score, and always
  requires a human to confirm before it counts as a match. Nothing is ever
  auto-merged.
- **Templates are per-facility**, each falling back to a shared/default
  template for that register family when the facility has none of its
  own. A facility whose form differs never breaks intake.
- **Only admins can create or approve an official template.** A data
  officer can flag that their form doesn't look right, but that flag
  has to be turned into an official template by an admin — never
  self-service.
- **Authentication** supports both magic-link sign-in and common SSO
  identity providers (Google, Microsoft/Azure AD, Okta, and similar) from
  the start.
- **Stale-facility alerting:** a facility that goes without a new intake
  for a configurable threshold (default 14 days) triggers a notification,
  sent on each recipient's own configured channel (email, SMS, or both).
  Neither the threshold nor the channel is hard-coded — both live in the
  platform configuration module (see "Platform configuration and
  notification preferences" in `02-data-model.md`), which is the general
  pattern for every tunable operational value in this build, not just
  this one alert.
- **Intake validation includes plausibility checks**, not just presence
  checks — physiologically implausible values (e.g. a blood pressure of
  300/10) are flagged for review, not silently accepted or silently
  blocked.
- **The full risk/referral rule engine, the full MVP metric set, and the
  healthcare-facing report generator are all in scope for this build** —
  none of this is "phase two."
- **A photographed paper register is the only intake channel.** There is
  no CSV/Excel upload — a data officer captures or uploads a photo of the
  register page, and AI/OCR extracts field values from the image and
  pre-fills a row. It never verifies or publishes itself. Every row lands
  as "review required" with a per-field confidence score, and a human
  must confirm or correct each low-confidence field before that row can
  publish. This is the same human-confirmation principle as identity
  linkage, applied to extraction instead of matching.
- **Light and dark mode, toggleable, on every screen.** Not a
  Next.js/Tailwind default left unstyled — a full second token set
  (colors, not just an inverted filter) that a person switches between
  from the top bar, with their choice remembered on their profile. See
  `09-ui-design-system.md`.
- **Cureva Care is multi-tenant.** One shared deployment serves every
  customer. Facilities are operated by Data officers and Facility leads,
  exactly as already designed; **organisations** (NGOs, government
  bodies, businesses — any buyer) are a separate, added-on layer that a
  Systems admin grants configurable, view-only access to a
  chosen set of facilities or regions, at a chosen access tier — never
  their own data-capture users (non-negotiable rule 7, above). See
  "Organisations and access scoping" in `01-product-scope.md`.
