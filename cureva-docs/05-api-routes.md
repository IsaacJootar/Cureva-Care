# Routes and API Surface

Cureva Care is a decoupled application: the Django backend exposes a REST API,
and the Next.js frontend is the only thing that renders pages — including
every admin screen. Nothing in the product is server-rendered by Django
directly.

## Frontend pages (Next.js)

| Route | Purpose | Access |
|---|---|---|
| `/login` | Magic-link request and SSO sign-in | Public |
| `/overview` | Facility (or, for an Organisation user, multi-facility) operating picture, priority changes | Facility lead, Organisation user |
| `/care-journey` | Booking, ANC contacts, delivery/PNC linkage funnel | Facility lead, Organisation user |
| `/needs-attention` | Actionable worklists with rule reasons | Facility lead only — see "Notes for implementation" |
| `/outcomes` | Maternal, birth, postnatal outcomes | Facility lead, Organisation user |
| `/facilities` | Readiness, reporting, quality, comparison | Facility lead, Organisation user |
| `/pregnancies/[episodeId]` | Identity-linked pregnancy timeline | Facility lead, Organisation user with identifiable access |
| `/records` | Source-faithful verified evidence, searchable/exportable | Facility lead, Organisation user (access-level filtered) |
| `/reports` | Saved briefs and portable dataset exports | Facility lead, Organisation user |
| `/intakes` | Search/select a facility via the workspace switcher, then capture or upload a photographed register batch; see your own intake history/status for that facility | Data officer |
| `/intakes/[id]/mapping` | Manual field-mapping and template-flag resolution | Systems admin only |
| `/intakes/[id]/confirm-fields` | Image-intake review: confirm/correct AI-extracted, low-confidence fields row by row | Data officer (their own batch), Facility lead (for their facility's batches) |
| `/admin/templates` | Template/version management | Systems admin only |
| `/admin/facilities` | Facility management — create/edit a facility via State → LGA → Ward picker | Systems admin only |
| `/admin/users` | User and role management | Systems admin only |
| `/admin/settings` | Platform configuration — every tunable threshold (stale-facility alert window, confidence cutoffs) with its current value, default, and description | Systems admin only |
| `/admin/organisations` | Create/edit an organisation account; grant or revoke its facility/region access and set the access tier per grant | Systems admin only |
| `/org/users` | An organisation's own user list — invite/manage other Organisation users within that organisation | Organisation user with `can_manage_org_users` |
| `/settings/notifications` | Each user's own notification-channel preference per notification type (email, SMS, both, or none) | All roles, own account only |
| `/identity-review` | Candidate identity matches awaiting confirmation | Facility lead only |

All of these are pages in the same Next.js app, sharing the same design
system — there is no visually or technically separate "admin area."

`/overview`, `/care-journey`, `/outcomes`, `/facilities`,
`/records`, and `/reports` are the exact same pages for both roles that
see them — a Facility lead's view is locked to their one facility (no
facility switcher, no cross-facility comparison), and an Organisation
user's view is locked instead to their organisation's granted
facilities/regions, which may be several facilities or many. This is
enforced by the backend API applying the caller's scope server-side (same
rule as the access-class enforcement below), not by the frontend hiding a
filter or a facility switcher. `/needs-attention` is not on this list —
see "Notes for implementation" below for why it's Facility-lead-only.
A Data officer and a Systems admin never reach these pages at all — a
Data officer's whole surface is `/intakes`
and its sub-routes; a Systems admin's is the `/admin/*` screens.

## Backend API (Django REST Framework)

| Method & path | Purpose |
|---|---|
| `POST /api/v1/intakes` | Data officer creates a batch against a chosen facility: register one or more register-page images (captured live via Capture Register, or uploaded via Upload Register) |
| `POST /api/v1/intakes/{id}/validate` | Run AI/OCR field extraction against the resolved template, then schema, type, and lineage validation |
| `GET /api/v1/intakes/{id}/progress` | Server-Sent Events stream: one event per field as it's extracted and matched, powers the live "scanning and matching" checklist; also carries the register-family-mismatch event when the cross-check flags one |
| `GET /api/v1/intakes/{id}/rows` | Extracted/matched rows for review, with a per-field confidence score on every row |
| `POST /api/v1/intakes/{id}/rows/{rowId}/confirm-field` | Confirm or correct one extracted field on one row |
| `POST /api/v1/intakes/{id}/publish` | Publish a batch idempotently — only once every row's low-confidence fields have been confirmed |
| `POST /api/v1/intakes/{id}/resolve-register-mismatch` | Data officer resolves a suspected wrong register family: confirm the declared family is correct, or switch to the detected one (re-resolves the template and re-runs extraction) |
| `POST /api/v1/intakes/{id}/flag` | Data officer flags a template mismatch |
| `GET /api/v1/intakes/{id}/mapping` | Unmatched extracted fields + open flags for the mapping screen |
| `GET /api/v1/my-intakes` | A data officer's own submission history across every facility they've ever submitted for, powers `/intakes`'s history view |
| `POST /api/v1/templates` | Systems admin creates/clones a template (shared or facility-specific) |
| `POST /api/v1/templates/{id}/aliases` | Systems admin adds an alias to an existing template version |
| `GET /api/v1/identity-candidates` | List pending candidate identity matches for review, scoped to the caller's facility |
| `POST /api/v1/identity-candidates/{id}/confirm` | Facility lead confirms a candidate match (merges into the Woman record) |
| `POST /api/v1/identity-candidates/{id}/reject` | Facility lead rejects a candidate match |
| `GET /api/v1/workspace` | First-paint context for the caller's scope: filters, summary, facilities, recent intakes |
| `GET /api/v1/maternal-summary` | Deterministic maternal metrics for a service-date window, scoped to the caller |
| `GET /api/v1/care-journey` | Pregnancy cohort and care-journey measures, scoped to the caller |
| `GET /api/v1/worklists` | Approved risk, referral, and follow-up items for the caller's one facility — **Facility lead only**, not reachable by an Organisation user |
| `POST /api/v1/worklists/{itemId}/action` | Facility lead records that they followed up on a worklist item — a note, timestamp, and who did it. Never edits the underlying register data or `referral_status`; it's an overlay audit record only, so the item can still resurface if the rule condition is still true after a later intake. See "Risk and follow-up rules" in `06-metrics-and-reporting.md`. |
| `GET /api/v1/records` | Paginated verified rows, scoped to the caller and access-level filtered |
| `GET /api/v1/pregnancies/{episodeId}` | Authorized pregnancy timeline and its evidence |
| `POST /api/v1/reports` | Generate and save an aggregate analytical brief, scoped to the caller |
| `GET /api/v1/facilities/{id}/status` | Reporting freshness, used by the stale-facility alert job |
| `GET /api/v1/states` | List states, for any State → LGA → Ward picker (facility creation, intake facility choice, or organisation access grants) |
| `GET /api/v1/states/{id}/local-governments` | List LGAs within a state |
| `GET /api/v1/local-governments/{id}/wards` | List wards within an LGA |
| `POST /api/v1/facilities` | Systems admin creates a facility, required `ward_id` (which fixes its LGA and State) |
| `POST /api/v1/organisations` | Systems admin creates an organisation account |
| `GET /api/v1/organisations` | Systems admin lists organisations |
| `PATCH /api/v1/organisations/{id}` | Systems admin edits an organisation's name, type, or active status |
| `POST /api/v1/organisations/{id}/facility-access` | Systems admin grants a facility- or region-level scope (facility, ward, LGA, or state) at a chosen access tier |
| `DELETE /api/v1/organisations/{id}/facility-access/{grantId}` | Systems admin revokes one access grant |
| `POST /api/v1/organisations/{id}/users` | An Organisation user with `can_manage_org_users` invites a colleague into their own organisation — always role `organisation_user`, never anything else |
| `GET /api/v1/organisations/{id}/users` | List an organisation's own users |
| `DELETE /api/v1/organisations/{id}/users/{userId}` | An Organisation user with `can_manage_org_users` deactivates a colleague they (or another `can_manage_org_users` user in the same organisation) invited — soft delete (`is_active = false`), never a hard delete; scoped strictly to their own organisation, rejected for any user outside it |
| `POST /api/v1/users` | Systems admin creates a Data officer, Facility lead, or another Systems admin (and, for a brand-new organisation's first user, an Organisation user with `can_manage_org_users` set) |
| `PATCH /api/v1/users/{id}` | Systems admin edits an existing user's name or role |
| `PATCH /api/v1/users/{id}/facility` | Systems admin assigns/changes which facility a Facility lead is scoped to |
| `POST /api/v1/users/{id}/deactivate` | Systems admin deactivates a user (`is_active = false`) — soft delete, never a hard delete; a deactivated user's past submissions/records are untouched (non-negotiable rule 1) |
| `POST /api/v1/users/{id}/reactivate` | Systems admin reactivates a previously deactivated user |
| `GET /api/v1/users` | Systems admin lists all users, their roles, and their facility/organisation assignments |
| `PATCH /api/v1/users/me` | Any signed-in user edits their own display name — name only; email and role are never self-service, always admin-set |
| `GET /api/v1/settings` | List every platform setting: key, value, type, default, description — powers `/admin/settings` |
| `PATCH /api/v1/settings/{key}` | Systems admin updates one platform setting's value, validated against its declared type (e.g. `stale_facility_alert_days`) |
| `GET /api/v1/users/{id}/notification-preferences` | A user's channel preference per notification type |
| `PATCH /api/v1/users/{id}/notification-preferences/{notificationType}` | A user sets their own channel (`email`\|`sms`\|`email_and_sms`\|`none`) for one notification type — self-service, no admin required |

## Notes for implementation

- Every dashboard/report endpoint above applies the caller's access
  class (aggregate / de-identified / identifiable) server-side — never
  trust a client-supplied access flag from the Next.js app. For an
  Organisation user, the same endpoints also filter to that
  organisation's effective facility set (see "Tenant scoping is read,
  never assumed" in `04-architecture-and-stack.md`) and cap the access
  class at whatever tier that organisation's grant allows, whichever is
  more restrictive. For a Facility lead, the same endpoints filter to
  their one `facility_id`.
- `/needs-attention`, `GET /api/v1/worklists`, and
  `POST /api/v1/worklists/{itemId}/action` are **restricted to Facility
  lead outright** — not just filtered by access tier like the
  dashboard/report endpoints above. An Organisation user caller is
  rejected server-side, the same way a capture/correct/resolve endpoint
  would reject one; this is a read restriction, not only a write one.
  Settled in the Roles & Operations review: organisations buy Cureva Care's
  intelligence, not its case-level worklist, and the underlying lens
  still reaches them — as a rolled-up "Open referrals" count from
  `GET /api/v1/maternal-summary` on their Overview, never a named-case
  list. See "Needs attention" in `01-product-scope.md` and
  `06-metrics-and-reporting.md`.
- Every capture/correct/resolve endpoint — intake creation, field
  confirmation, publish, identity-candidate confirm/reject, template
  create/flag/mapping, settings, user management, worklist actioning —
  rejects any caller whose role is Organisation user, regardless of
  what the frontend shows. Organisation-side access is read-only at the
  API layer, not just hidden in the UI. The one deliberate exception is
  narrow and explicit: `DELETE /api/v1/organisations/{id}/users/{userId}`
  is the single write an Organisation user can make, gated on
  `can_manage_org_users`, scoped only to their own organisation's own
  invited users — never another organisation's, and never a Facility
  lead, Data officer, or Systems admin account.
- `PATCH /api/v1/users/{id}` and `PATCH /api/v1/users/me` are two
  different endpoints on purpose, not one endpoint with a looser
  permission check: the admin-scoped one can change name or role, the
  self-scoped one can only ever change the caller's own name. Enforce
  this server-side even though the two look similar — `me` must reject
  any `role` field in its body outright rather than silently ignoring
  it.
- `POST /api/v1/intakes/{id}/publish` must be safe to call twice with the
  same ID (idempotent) — rely on the intake's `status` field and a
  database transaction, not client-side "don't double click" logic.
- CORS must be configured so only the Cureva Care Next.js frontend's origin(s)
  can call the API with credentials.
- Auth: the Next.js app never talks to identity providers directly for
  session issuance — Django owns magic-link generation and the OAuth/OIDC
  handshake, and hands back a session/JWT the frontend then uses for
  every subsequent API call.
