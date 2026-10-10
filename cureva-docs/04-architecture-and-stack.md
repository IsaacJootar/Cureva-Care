# Architecture and Stack

## Chosen stack

| Component | Choice | Reason |
|---|---|---|
| Backend | Python + Django, exposing a REST API via Django REST Framework | Python has the strongest ecosystem for the actual hard problem here — parsing, cleaning, and validating messy tabular health data. Django bundles ORM, auth, jobs, and admin tooling in one framework. |
| Database | PostgreSQL | Transactions, auditability, JSONB for template/lineage data, strong analytical SQL. |
| Frontend | One Next.js (React) application, styled with Tailwind CSS | The single, consistent UI for the entire product — dashboards and every internal admin screen alike. No second, differently-styled interface anywhere. |
| Object storage | S3-compatible private bucket | Immutable source-file retention with signed, time-limited access. |
| Background jobs | Database-backed task queue (e.g. `django-q2`) | Avoids adding Redis/a message broker as a separate moving part unless real throughput later requires it. |
| Live upload progress | Server-Sent Events (SSE) from Django, one-directional stream of per-field extraction events | Powers the real-time "scanning and matching" checklist on the upload screen; simpler than a full WebSocket for a one-way progress feed, no extra infrastructure needed. |
| Authentication | Django as the identity authority: magic-link email sign-in plus OAuth/OIDC for common SSO providers (Google, Microsoft/Azure AD, Okta, etc.), issuing session/JWT credentials the Next.js app uses to call the API | Covers both simple facility-level accounts and enterprise-identity organisations without picking just one from day one. |
| Analytics | SQL views + a daily aggregate table, refreshed by a scheduled job after each publish | Deterministic and explainable; no separate analytics warehouse needed at this scale. |
| Narrative reports | Optional aggregate-only LLM call from the backend | Turns already-computed, non-identifiable metrics into prose. Never sees row-level data. |
| OCR / vision extraction | Claude (Anthropic) vision API, called from Django | Default pilot choice — strong handwriting/document reading, one vendor relationship. Swappable behind `extraction_engine` (see `03-templates-and-intake.md`) if pilot accuracy testing favors a different provider. |
| SMS delivery | [Termii](https://termii.com/) | **Settled choice**, not a pilot placeholder — an African/Nigeria-focused messaging API (SMS, with WhatsApp/voice/email available if ever needed), API-key authenticated, used for the stale-facility alert and any future SMS notification type. Credential lives in an environment variable (e.g. `TERMII_API_KEY`), never in `platform_settings` — see the Secrets row below. Still integrated behind the notification job's own interface, not called directly from other modules, so swapping the provider later stays a one-module change even though it's no longer an open decision. |
| Secrets | Environment variables / the hosting platform's secrets manager — never `platform_settings`, never committed to source | API keys (vision/OCR, SMS, email), database credentials, and signing keys are configuration a deploy needs, not something an admin edits at runtime. Kept structurally separate from the admin-editable `platform_settings` table (see `02-data-model.md`) so a real secret can never end up exposed in an admin-visible screen. |

## Why this split (backend vs. frontend)

Django and Next.js are two separate applications talking over an API, not
one merged framework. This is intentional: it lets the backend focus
entirely on being correct (data integrity, validation, the append-only
publish rule) while the frontend focuses entirely on being good to use
(one consistent, modern, Tailwind-styled interface for literally every
screen in the product, including the admin tools). Django's own built-in
admin panel is not used anywhere in the shipped product — every admin
screen (facilities, templates, roles, rules) is a real page in the Next.js
app, calling the same API a data officer's screens call, just with
different permissions.

## Service boundaries (inside the Django backend)

Structure the Django project into these logical apps, even though they
deploy together as one backend:

| Module | Owns | Does not own |
|---|---|---|
| Identity & Access | Users, organisations and their facility/region access grants (`organisation_facility_access`), roles, invitations, SSO/magic-link auth, platform configuration (`platform_settings`) and per-user notification preferences | Clinical data |
| Register Intake | Files, templates, template flags, batches, jobs, review, publication | Metric definitions |
| Maternal Projection | Woman, episode, and maternal event contracts, identity candidates | Source deletion or rewriting |
| Intelligence | Metric definitions, aggregates, worklists, exports | Clinical treatment decisions |
| Reporting | Charts, saved briefs, report audit | Unbounded access to source rows |

Keeping these as separate Django apps (even in one deployable project)
enforces the rule that nothing outside Register Intake ever writes to a
source row, and nothing outside Maternal Projection writes a
Woman/Episode/Event record directly.

**Configuration is read, never inlined.** Every other module treats
`platform_settings` (owned by Identity & Access, see
`02-data-model.md`) as the only source of truth for a tunable
operational value — the stale-facility alert window, confidence
thresholds, and any value added later. A settings value is loaded
through one shared accessor (cached with a short TTL and invalidated on
write, so a change from `/admin/settings` takes effect within seconds,
not after a redeploy) rather than each module reading the table
directly or, worse, re-declaring its own constant. The same rule holds
for notification channels: a job that sends a notification resolves the
recipient's `notification_preferences` row rather than assuming a
channel. This is enforced at code review, not just by convention — a
literal threshold or hard-coded channel anywhere outside this accessor
is a defect.

**Tenant scoping is read, never assumed.** Every endpoint that returns
dashboard, report, or record data checks the caller's role first: a
Facility lead is scoped by their own `facility_id`; an Organisation user
is scoped by their organisation's effective facility set — the union of
every explicit and region-level grant in `organisation_facility_access`
(see `02-data-model.md`) — resolved server-side on every request, never
trusted from a client-supplied facility list. A Data officer never calls
these endpoints at all (their surface is the intake pipeline only, scoped
to their own submitted batches — see `03-templates-and-intake.md`), and a
Systems admin gets no default dashboard access either, per least
privilege. The same endpoint code path serves both kinds of dashboard
caller (Facility lead and Organisation user); only the resolved scope
differs.

**External service failures don't fail silently.** The vision/OCR call
and the SMS/email send are the two external dependencies in this build,
and each has its own failure handling: extraction failure moves an
intake to `extraction_failed` with a bounded, backed-off retry and a
manual retry action for the data officer (see
`03-templates-and-intake.md`); a failed notification send is logged and
retried per channel independently, and never blocks or fails the event
it was notifying about — a stale-facility check still marks a facility
stale even if that run's SMS send fails.

## Data flow summary

```
Register photo upload — Capture Register or Upload Register
  (Next.js form → Django API)
  → Register Intake app: fingerprint, template resolution, AI/OCR field
    extraction, validate
  → each field result streamed back over SSE as it resolves, driving
    the live "scanning and matching" checklist in the Next.js upload screen
  → source_rows table (raw + normalized, status =
    awaiting_confirmation/verified/rejected)
  → mandatory field-confirmation gate: every low-confidence field confirmed
    or corrected by a human reviewer
  → identity resolution (strict fast path, then candidate matching)
  → Maternal Projection app writes Woman / PregnancyEpisode / ANCContact /
    BirthEvent / PNCContact / Referral records
  → Intelligence app: scheduled job recomputes daily_facility_metric rows
  → Next.js dashboard reads only from Intelligence-app API endpoints for
    anything beyond the Records/evidence view, which reads source_rows
    directly under the caller's access level
```

## Performance and reliability targets

- p95 under two seconds for the main dashboard across a
  twelve-month window and the pilot's facility count.
- First-paint dashboard data returned in one API call; row explorers and
  pregnancy timelines load lazily from the Next.js app.
- Daily facility metrics precomputed after each publish, rebuilt
  idempotently (safe to re-run without double-counting).
- Row-level views are paginated; identity-linkage lookups are capped by
  facility and date range.
- Publication runs inside a database transaction with a unique constraint
  on `(facility_id, register_family, source_hash)` to
  guarantee idempotency even under retries.
- Structured logs exclude names, phone numbers, card numbers, and any
  clinical free text (see `07-security-privacy-access.md`).
- Monitor: API latency, job queue age, failed intakes, pending rows, open
  template flags, report generation failures, stale (non-reporting)
  facilities.

## Testing strategy

| Layer | Required tests |
|---|---|
| Mapping | Golden-file tests per template version (including per-facility templates): blank values, repeated serials, malformed dates |
| Publication | Checksum idempotency, append-only behaviour, rollback on failure |
| Identity linkage | Strict-match correctness, candidate-match confidence scoring, no auto-merge without confirmation |
| Analytics | Fixture-based metric reconciliation, denominator rules, service-date filtering |
| Access | Aggregate / de-identified / identifiable access tests, audit-event generation |
| UI | Filter consistency, partial failure states, empty states, export parity, consistent design across dashboard and admin screens |
| Recovery | Database restore and source-file recovery exercise before launch |
