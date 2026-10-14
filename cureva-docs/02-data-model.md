# Data Model

## Two-layer design

The **source layer** keeps the register exactly auditable. The **maternal
layer** gives analytics a stable clinical vocabulary. A verified source row
may create or update exactly one canonical event, but the source row and
every field transformation remain linked to it permanently.

| Layer | Core entities | Purpose |
|---|---|---|
| Source and lineage | Intake, source file, template version, source row, correction history | Faithful evidence, review, idempotency, audit |
| Maternal domain | Woman, pregnancy episode, ANC contact, birth event, PNC contact, referral, outcome | Continuity, worklists, analytical definitions |
| Intelligence | Daily facility metric, quality metric, saved report, export audit | Fast dashboards, reproducible reporting |

## Core entity contract

| Entity | Required fields | Important rule |
|---|---|---|
| **Intake** | facility, register_family, template_version, source_hash, received_at | Immutable and unique by (facility, register_family, source_hash). Duplicate checksum = no-op. |
| **Source row** | intake_id, row_number, raw_payload (JSONB), service_date, status | Serial/card numbers may legitimately repeat across intakes — never used alone for duplicate detection. |
| **Woman** | internal_id (generated), facility_id, stable_identifier, access_class | Created automatically via a stable identifier match, or via a human-confirmed candidate match (see identity linkage below). Never auto-merged on demographic similarity alone. |
| **Pregnancy episode** | woman_id, episode_id, booking_date, lmp_or_edd, status | One woman may have multiple episodes over time — never a 1:1 relationship. |
| **ANC contact** | episode_id, service_date, contact_number, facility_id, source_row_id | Store gestational age exactly as written, plus its unit (weeks vs. months) — never silently convert. |
| **Birth event** | episode_id, delivery_date, place, mode, maternal_outcome, baby_outcome | Must support one or more babies per birth event — never assume single-baby. |
| **PNC contact** | episode_id, subject (mother\|newborn), service_date, source_row_id | Mother and newborn observations stay in clearly separate fields — never merged into one ambiguous record. |
| **Referral** | episode_id, reason, origin, destination, date, status | Must support both "open" and "closed with documented outcome" states. |

## Minimum dataset (per domain)

| Domain | MVP fields |
|---|---|
| Identity and location | Woman name, card/folder number, phone, address/settlement, age or DOB, facility |
| Pregnancy episode | Gravida, parity, LMP, EDD, gestational age at booking, previous obstetric risk as recorded, episode status |
| ANC contact | Service date, contact number, gestational age, blood pressure, weight, fundal height, fetal heart rate, presentation, symptoms/findings |
| Screening | Haemoglobin, blood group/Rh, HIV, syphilis, hepatitis B, malaria testing, urine protein/glucose, other test as written |
| Interventions | Iron and folate, tetanus vaccination, IPTp, counselling, treatment as written, referral, next appointment |
| Delivery | Date/time, place, mode, attendant, complications, maternal outcome, birth outcome, baby sex, birth weight, referral |
| Postnatal | Contact date, time since birth (if recorded), maternal assessment, newborn assessment, feeding, danger signs, outcome, referral |
| Lineage | Source row, raw value, normalized value, correction history, verifier, template version, publication timestamp |

## Roles, organisations, and users

**Four roles, that's it** — see `01-product-scope.md`'s "Roles" section
for the full behavioural spec; this is just the schema they run on.

- **Data officer** — Cureva Care's own internal staff. Not tied to one
  facility: they choose which facility a batch belongs to at the start
  of each intake (see `03-templates-and-intake.md`). No `facility_id` on
  their user row — their facility association lives on the intake, not
  on the person.
- **Facility lead** — the clinical reviewer at one facility. Every
  facility has one. `facility_id` set.
- **Organisation user** — view-only, at whichever facilities/regions
  their organisation was granted. `organisation_id` set.
- **Systems admin** — the final configuration authority: creates
  facilities, approves templates, creates organisations and sets their
  facility/region grants, creates users. No `facility_id` or
  `organisation_id` — this role isn't scoped to one facility or one
  organisation, it configures the whole system.

```sql
CREATE TABLE organisations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    org_type    TEXT NULL,      -- free text, e.g. 'NGO', 'Government', 'Private/business' — not an enforced enum
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_by  UUID NULL REFERENCES users(id),   -- always a Systems admin
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Which facilities (or whole regions) an organisation can view, and at
-- what access tier. A region-level grant auto-expands to every facility
-- under that node, present and future — granting a whole State or LGA
-- doesn't need re-granting when a new facility is added under it later.
CREATE TABLE organisation_facility_access (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID NOT NULL REFERENCES organisations(id),
    scope_type      TEXT NOT NULL,   -- 'facility' | 'ward' | 'local_government' | 'state'
    scope_id        UUID NOT NULL,   -- id of the facility/ward/LGA/state granted, per scope_type
    access_level    TEXT NOT NULL DEFAULT 'aggregate', -- 'aggregate' | 'de_identified' | 'identifiable' — same three tiers as 07-security-privacy-access.md
    granted_by      UUID NOT NULL REFERENCES users(id), -- always a Systems admin; never self-service
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id       UUID NULL REFERENCES organisations(id), -- set only for Organisation user
    facility_id           UUID NULL REFERENCES facilities(id),    -- set only for Facility lead
    role                  TEXT NOT NULL, -- 'data_officer' | 'facility_lead' | 'organisation_user' | 'systems_admin'
    can_manage_org_users  BOOLEAN NOT NULL DEFAULT false, -- only meaningful when role = 'organisation_user': lets this person invite/manage their own organisation's other users. Set by a Systems admin when the organisation's first user is created.
    name                  TEXT NOT NULL,
    email                 TEXT NOT NULL UNIQUE,
    phone                 TEXT NULL,
    theme_preference      TEXT NOT NULL DEFAULT 'system', -- light | dark | system, see below
    is_active             BOOLEAN NOT NULL DEFAULT true,
    created_by            UUID NULL REFERENCES users(id),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

A user row never has both `organisation_id` and `facility_id` set — an
Organisation user never operates a facility, and a Facility lead is
never part of a customer organisation. A Data officer and a Systems
admin have neither set: a Data officer's facility association lives on
each intake, not on the person (see "Who submits data, and for which
facility" in `03-templates-and-intake.md`); a Systems admin isn't scoped
to any one facility or organisation at all.

`organisations` grows continuously — every new customer account is a new
row, created only by a Systems admin, never self-service sign-up (same
invite-only posture as every user account, see
`07-security-privacy-access.md`).

## Facility administrative hierarchy (State → LGA → Ward → Facility)

Every facility is created under a location, not floating on its own: a
facility belongs to a **Ward**, a ward belongs to a **Local Government
Area (LGA)**, and an LGA belongs to a **State**. This is a strict
four-level hierarchy, matching the real administrative structure
facilities already sit inside — it's not a free-text "region" field, it's
three linked lookup tables plus the facility itself.

```sql
CREATE TABLE states (
    id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name   TEXT NOT NULL UNIQUE
);

CREATE TABLE local_governments (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state_id UUID NOT NULL REFERENCES states(id),
    name     TEXT NOT NULL,
    UNIQUE (state_id, name)
);

CREATE TABLE wards (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    local_government_id UUID NOT NULL REFERENCES local_governments(id),
    name                TEXT NOT NULL,
    UNIQUE (local_government_id, name)
);

CREATE TABLE facilities (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ward_id       UUID NOT NULL REFERENCES wards(id),
    name          TEXT NOT NULL,
    facility_type TEXT NULL,      -- e.g. PHC, general hospital, maternity home
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

A facility only ever stores its `ward_id` — its LGA and State are always
derived by joining up through `local_governments` and `states`, never
duplicated onto the facility row itself. That keeps the hierarchy as a
single source of truth: renaming or correcting an LGA updates every
facility under it automatically, nothing to re-save facility by facility.

**Creating a facility (Systems admin only, `/admin/facilities`)** is a
guided three-step picker, in order: choose the State, which narrows the
LGA list to that State's LGAs; choose the LGA, which narrows the Ward
list to that LGA's wards; choose the Ward, then name the facility. A
facility cannot be created without all three selected — there's no
"unassigned" facility. States and LGAs and wards themselves are seeded
once from the national administrative list (not invented per facility),
so admins are always picking from a fixed list, not free-typing names
that could drift out of sync facility to facility.

This hierarchy is also how the Facilities screens filter and group —
"all facilities in Kano State," "all facilities in this LGA" — rather
than a flat, unstructured region tag, and it's the structure behind the
guided State → LGA → Ward picker used for one-off setup tasks like
facility creation. A Data officer's own facility choice is a separate,
faster control — a flat search over facility name/LGA/state in the
workspace switcher, not a walk through this hierarchy (see "Workspace
switcher (Data officer)" in `09-ui-design-system.md` and "Who submits
data, and for which facility" in `03-templates-and-intake.md`) — every
row it resolves to is still a `facility_id` from this same table, just
reached by search instead of drill-down. This hierarchy is also what an
organisation's region-level
access grant (above) resolves against.

## Date semantics

- `service_date` — the date care occurred. Drives every date filter and
  clinical trend. Non-negotiable rule #4.
- `batch_period_from` / `batch_period_to` — the service dates represented in
  an intake batch.
- `received_at` — when Cureva Care received the source file.
- `published_at` — when the evidence became available for analysis.
- No dashboard, chart, or export may substitute `received_at` or
  `published_at` for `service_date`.

## Identity and episode linkage (strict fast path + probabilistic candidate matching)

> **Note:** `IDENTITY_MATCHING_UPDATE.md` extends and, where it conflicts,
> supersedes this section — the strict path now requires a matching name and a
> recent sighting on top of the card number, a woman is recognised by any of
> her identifiers (`woman_identifiers`), and episode boundaries follow explicit
> rules. See that file and `DECISIONS.md`.

Two linkage paths, both built:

**1. Strict fast path.** A source row is linked into a Woman/Pregnancy
record automatically when it carries a stable identifier — a facility
card/folder number or an equivalent facility-issued ID — that matches an
existing Woman exactly. This is the default, preferred path and requires no
human review.

**2. Probabilistic candidate matching.** When no stable identifier is
present, or the identifier doesn't match anything on file, the system
generates a candidate match against existing Women using available
demographics (name, date of birth, facility, phone number where present)
and assigns it a visible confidence score. Candidate matches are never
auto-merged:

- Below a configurable high-confidence threshold, the record stays an
  unlinked encounter — still stored, still counted in
  operational/completeness metrics, still analyzable on its own.
- At or above the threshold, it appears in a review queue for an authorized
  user (facility lead) to confirm or reject. Only a
  human confirmation actually merges it into a Woman/Pregnancy record.
- Every confirmation and rejection is an audit event, referencing the
  matching fields and the confidence score shown at the time.

`identity_candidates` table:

```sql
CREATE TABLE identity_candidates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_row_id   UUID NOT NULL REFERENCES source_rows(id),
    candidate_woman_id UUID NOT NULL REFERENCES women(id),
    confidence      NUMERIC(4,3) NOT NULL,   -- 0.000–1.000
    matched_fields  JSONB NOT NULL,          -- which fields contributed, and how
    status          TEXT NOT NULL DEFAULT 'pending', -- pending|confirmed|rejected
    reviewed_by     UUID NULL REFERENCES users(id),
    reviewed_at     TIMESTAMPTZ NULL
);
```

A record only contributes to per-woman continuity metrics (contact counts,
ANC-to-delivery linkage, etc.) once it is linked — either via the strict
path or a confirmed candidate. Unlinked and unconfirmed records are always
included in facility-level operational counts, just not in per-woman
continuity analysis, so nothing is silently dropped from the picture.

## Worklist actions (audit overlay, never a data edit)

Settled alongside the Roles & Operations review: a Facility lead can mark
a risk/referral/follow-up worklist item as followed up on
(`POST /api/v1/worklists/{itemId}/action`, see `05-api-routes.md`). This
follows the same shape as identity-candidate review above — a separate
overlay table, never a mutation of the underlying register data or the
`referral_status` field captured on the source row (non-negotiable rule
1: raw and clinically-documented values are never touched). A worklist
item is computed from the maternal model, not stored as its own row, so
the action needs its own durable record to point back at:

```sql
CREATE TABLE worklist_actions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_key        TEXT NOT NULL,            -- which risk/referral/follow-up rule this item came from
    subject_type    TEXT NOT NULL,            -- 'pregnancy_episode' | 'referral' | 'pnc_contact', etc.
    subject_id      UUID NOT NULL,            -- the id of that subject row
    facility_id     UUID NOT NULL REFERENCES facilities(id),
    note            TEXT NULL,
    actioned_by     UUID NOT NULL REFERENCES users(id),
    actioned_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

An actioned item is **not** dismissed permanently — if the same rule
still evaluates true against the subject after a later intake (e.g. the
danger sign is still undocumented as resolved), it resurfaces on the
worklist again, now showing its action history alongside the current
flag. This mirrors non-negotiable rule 6 (blank/unresolved is never
silently treated as resolved) applied to follow-up action, not just to
missing fields. `GET /api/v1/worklists` joins against this table so the
UI can show "Last actioned 3 days ago by I. Johnson-Bello" on an item
that's still open.

## Platform configuration and notification preferences

Every operational value that a real deployment will want to tune —
without waiting on a code change — lives here, and only here. Nothing
in Cureva Care reads an alert threshold, a confidence cutoff, or a
notification channel from a constant in application code; every such
value is read at runtime from `platform_settings`, so a Systems
admin can change it from `/admin/settings` and have it take
effect immediately. This is the "Configuration over hard-coding"
principle from `01-product-scope.md`, made concrete as one table
instead of scattered settings.

**`platform_settings`** — a curated key/value store, not a free-for-all:
only keys the product explicitly defines are writable, each with a
declared type, a default, and a description shown in the admin UI.

```sql
CREATE TABLE platform_settings (
    key          TEXT PRIMARY KEY,         -- e.g. 'stale_facility_alert_days'
    value        JSONB NOT NULL,           -- typed value, validated against the key's declared type
    value_type   TEXT NOT NULL,            -- integer|decimal|boolean|string
    description  TEXT NOT NULL,            -- shown in the admin settings UI
    updated_by   UUID NULL REFERENCES users(id),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Every setting is seeded with a sensible default at migration time, so the
system is fully operational before an admin ever visits the settings
screen — "configurable" never means "unset." The keys this build ships
with:

| Key | Type | Default | Used by |
|---|---|---|---|
| `stale_facility_alert_days` | integer | `14` | Stale-facility alerting job, see `06-metrics-and-reporting.md` |
| `identity_candidate_confidence_threshold` | decimal | `0.75` (starting default — see `08-delivery-plan.md`) | Identity candidate matching, above |
| `ai_extraction_confidence_threshold` | decimal | `0.85` | AI/OCR field-confirmation gate, see `03-templates-and-intake.md` |
| `register_mismatch_min_signal` | integer | `2` | Register-family cross-check — minimum matched signature fields before flagging a suspected wrong register, see `03-templates-and-intake.md` |

Adding a new tunable value later means adding a row to this table (with a
migration seeding its default) and reading it at the call site — never
adding a new hard-coded constant elsewhere in the codebase. A code review
that finds a literal threshold, delay, or channel choice outside this
table is treated as a bug.

**`notification_preferences`** — every notification Cureva Care sends (a
stale-facility alert, or any future notification type) is routed through
a per-user, per-notification-type channel preference, never a single
channel hard-coded for everyone:

```sql
CREATE TABLE notification_preferences (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES users(id),
    notification_type  TEXT NOT NULL,   -- e.g. 'stale_facility_alert'
    channel            TEXT NOT NULL DEFAULT 'email_and_sms', -- email|sms|email_and_sms|none
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, notification_type)
);
```

Rules:

- Every user gets a default row per notification type at account
  creation (`email_and_sms`, matching today's behaviour), but any user
  can change their own channel for any notification type from their own
  account settings — a Systems admin does not have to do this
  on their behalf.
- A notification job (e.g. the stale-facility alert) never assumes a
  channel. It resolves its recipients (by role and facility scope),
  looks up each recipient's `notification_preferences` row for
  that `notification_type`, and sends on exactly the channel(s) recorded
  there — `none` means that recipient is silently skipped, not defaulted
  back to email.
- This table is what makes "any role that configures how to receive
  notifications" real: the preference lives with the user, not with the
  alert job, so adding a second notification type later never means
  touching the stale-facility alert code.

**Theme preference** is the same idea applied to light/dark mode: a
`theme_preference` column on the user record (`light` \| `dark` \|
`system`, default `system`), set from the theme toggle in the top bar
(see "UI Design System" in `09-ui-design-system.md`) and read on login
so the choice follows the person across devices, not just remembered in
one browser's `localStorage`.
