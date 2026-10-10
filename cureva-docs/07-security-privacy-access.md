# Security, Privacy, and Access

## Access model

| Level | Can see | Typical user |
|---|---|---|
| Aggregate | Counts, rates, charts, reports only | Leadership, funder, broad organisation viewer |
| De-identified rows | Clinical rows without declared identity fields | Analyst or research partner |
| Identifiable rows | Full authorized register evidence and pregnancy timelines | Clinical follow-up team or owning authority |

Default posture: every role gets the least access it needs. Identifiable
access is explicit, authorized, and audited — never the default for a new
role. This applies with extra weight to **organisation accounts** (the
SaaS customer layer — see "Organisations and access scoping" in
`01-product-scope.md`): a new organisation's access grant defaults to
**Aggregate**, the least-identifiable tier, and raising it to
De-identified or Identifiable is a deliberate, per-grant decision a
Systems admin makes — not something an organisation gets by
default just for being a paying customer.

## Minimum controls (MVP)

- Organisation scoping on every query for an Organisation user; facility
  assignment for a Facility lead. For an Organisation user specifically,
  scoping means their organisation's effective facility set from
  `organisation_facility_access` (see `02-data-model.md`) — resolved
  server-side on every request, never trusted from the client.
- **Organisation accounts are read-only at the API layer, not just in the
  UI.** Every endpoint that creates, corrects, uploads, or resolves
  anything (intake, identity candidate, template, settings, user
  management outside an organisation's own user list) rejects a caller
  whose role is Organisation user outright. An
  organisation with no write path in the UI but a reachable write
  endpoint underneath is treated as a defect, not a UI oversight.
- Encryption in transit and at rest; private source-file storage; short-
  lived signed URLs for any file access.
- Audit events for: identity views, searches, exports, corrections,
  publication, role changes, and organisation access-grant changes
  (creating an organisation, granting or revoking a facility/region, or
  changing its access tier).
- No PHI (names, phone numbers, card numbers, free-text clinical notes) in
  application logs, error payloads, monitoring labels, or any LLM prompt —
  this is a hard requirement, not a nice-to-have.
- Configurable retention for source files, records, exports, and audit
  logs, aligned to legal requirements (to be confirmed with
  stakeholders — see `08-delivery-plan.md`).
- Backup, restore, and incident-response procedures tested before live
  maternal data is accepted.
- A clinical governance register tracking metric definitions, rules,
  changes, approvals, and effective dates.
- **Secrets are never platform configuration.** API keys (vision/OCR,
  SMS, email), database credentials, and signing keys live in
  environment variables or the hosting platform's secrets manager — never
  in the admin-editable `platform_settings` table, never committed to
  source, and never visible through any admin screen. `platform_settings`
  is for operational values an admin should be able to tune (a threshold,
  a channel default); secrets are a deploy-time concern, kept structurally
  separate so a real credential can never end up exposed where an admin
  screen is.
- **Applicable law.** Maternal PHI handled here falls under Nigeria's Data
  Protection Act (NDPA 2023) and its implementing regulation. Where an
  organisation customer's own funder imposes additional security
  requirements on top of that (e.g. a PEPFAR or Global Fund security
  addendum), those requirements layer on top of this section's controls,
  never replace them. Data residency/hosting region (open decision #4 in
  `08-delivery-plan.md`) should be confirmed against NDPA's requirements
  specifically, not decided on cost/performance grounds alone.
- Login and magic-link-request endpoints are rate-limited per email and
  per IP, to prevent credential-stuffing and magic-link-flooding abuse.

## Authentication

Both magic-link and SSO are supported from the start, both issued by
Django and consumed by the Next.js frontend as a session/JWT:

- Invite-only account creation — no public sign-up, either path. Only the
  Systems admin creates an account, assigns its role, and (for a
  Facility lead) assigns its facility — never self-selected by the
  invitee. Magic-link or SSO only ever establishes *who* someone is; it
  never grants or changes *what* they can see — role and facility
  assignment come exclusively from the admin-managed record in
  `/admin/users` (see `05-api-routes.md`), looked up at login, not
  supplied by the login method itself.
- Magic links are single-use and short-lived (e.g. 15 minutes).
- SSO covers common OAuth2/OIDC providers (Google, Microsoft/Azure AD,
  Okta, and similar) — an organisation can be configured to
  require SSO instead of magic-link if needed.
- Every login event, on either path, is an audit event.

## Data interpretation policy

Cureva Care reports recorded service activity and outcomes, not ground truth.
The application and its UI must consistently:

- Distinguish encounters from unique women (see the identity linkage rules
  — strict fast path plus human-confirmed candidate matching — in
  `02-data-model.md`).
- Distinguish linked episodes from unlinked/unconfirmed records.
- Distinguish facility register counts from population rates — Cureva Care does
  not claim population-level prevalence.
- Treat missing fields as missing, never as a negative/normal finding.
- Never present correlation as causation in any generated report.
- Show reporting completeness and case-mix limitations alongside any
  facility comparison.
