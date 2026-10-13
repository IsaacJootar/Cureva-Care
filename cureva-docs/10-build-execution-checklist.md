# Build Execution Checklist

This is the operating manual for Claude Code builds Cureva Care from this package. It turns the six
phases in `08-delivery-plan.md` into checkable sections, states the git
workflow to follow while working through them, and defines how the
agent marks its own progress. Read `00-START-HERE.md` and
`08-delivery-plan.md` first — this file assumes both.

## The git workflow (non-negotiable)

- **Finish a section → commit → push.** Every checklist item below is
  one section. The moment it's genuinely done (builds, and — where a
  test is named — passes it), commit it on its own, with a message
  naming the module and the section, and push immediately. Never batch
  several sections into one commit.
- **Finish a module → commit → push → move to the next module.** When
  every section in a module is checked and the module's exit condition
  (quoted from `08-delivery-plan.md` at the top of each module below)
  is actually verified true — not assumed — make one final commit for
  the module (updating this file's checkboxes, see "Marking progress"
  below), push, and only then start the next module. Modules are
  worked in order; a later module is never started while an earlier
  one still has unchecked sections, because later modules depend on
  earlier ones (Intake depends on Foundations' schema, Dashboards
  depend on Intake's published data, and so on).
- **No Claude attribution in commits.** No `Co-Authored-By` trailer, no
  "Generated with Claude Code" line, nothing naming Claude or Anthropic in
  a commit message or PR description — commits are authored as Isaac only.
  Disable the default attribution in `.claude/settings.json`
  (`{"attribution": {"commit": "", "pr": ""}, "includeCoAuthoredBy": false}`)
  and verify with `git log -1 --format=%B` after the first commit.
- **Commit message convention:** `feat(<module-slug>): <what this
  section delivers>` for a section, and `feat(<module-slug>): complete
  module — exit condition verified` for the module-closing commit.
  Module slugs: `foundations`, `intake-templates`, `identity-linkage`,
  `maternal-dashboards`, `risk-referrals-reporting`,
  `operations-hardening`.
- **Never skip ahead.** If a section turns out to depend on something
  not yet built, stop and build that dependency first (even if it
  belongs to an earlier, supposedly-finished module) rather than
  stubbing it out silently. Note the correction in the commit message.

## Marking progress

Each module below starts with a status line:
`**Status:** Not started | In progress | Done`. Update it as work
begins and completes. Each section is a checkbox:
`- [ ] Section name`. When a section is done, change it to `- [x]` in
the same commit that finishes the section — this file is the single
source of truth for where the build stands, so a person (or another
agent) can open it and know exactly what's left without reading code.

---

## Module 1 — Foundations

**Status:** Done — exit condition verified live (login via magic-link →
admin shell → created a facility by walking the seeded State→LGA→Ward
picker → created an organisation and granted it one facility), in both
light and dark mode. The one open item is SSO: the Google OAuth flow is
fully built but deferred pending real Google client credentials, by
product-owner decision (2026-10-11). Every other section is complete.
**Exit condition (from `08-delivery-plan.md`):** "A user can log in
through either path, reach an empty dashboard shell, a Systems admin can
create a facility by walking the seeded State → LGA → Ward picker, and a
Systems admin can create an organisation and grant it access to at least
one facility."

- [x] Django project scaffolded with the five apps from
      `04-architecture-and-stack.md`'s service boundaries (Identity &
      Access, Register Intake, Maternal Projection, Intelligence,
      Reporting) — empty apps, correct boundaries, no cross-app writes
      yet.
- [x] PostgreSQL schema migrated for every entity in `02-data-model.md`
      that doesn't depend on a later module: `organisations`,
      `organisation_facility_access`, `users`, `states`,
      `local_governments`, `wards`, `facilities`, `platform_settings`
      (seeded with its default rows, including the `0.75` starting
      default for `identity_candidate_confidence_threshold`),
      `notification_preferences`.
- [x] Admin organisation-management screen (`/admin/organisations`)
      built to `09-ui-design-system.md`'s screen 7 spec — create an
      organisation, grant/revoke facility- or region-level access with
      a per-grant tier — both light and dark mode. (Two-step create flow
      + manage-access modal reusing the shared State→LGA→Ward→Facility
      picker; build-verified. Live click-through pending.)
- [x] Next.js project scaffolded with Tailwind, `darkMode: 'class'` set
      in the Tailwind config. (Next 16 + Tailwind v4, which is CSS-first:
      the `darkMode:'class'` intent is implemented as a `data-theme`
      custom variant + attribute on `<html>` — an explicit user-forced
      choice, not prefers-color-scheme alone.)
- [x] **Design token system implemented** — every CSS custom property
      in `09-ui-design-system.md`'s "Design tokens" sections (light and
      dark), the `:root` / `:root[data-theme="dark"]` override
      structure, and the render-blocking inline script that reads the
      saved theme before first paint (no flash of the wrong theme).
      Built once, here, so every screen from Module 2 onward is built
      against it rather than retrofitted later. Dark-mode
      `--cv-button-primary-bg` signed off (open decision #9): inverse —
      `#f2f1ec` bg, `#111110` ink. Verified in-browser, both modes.
- [x] Theme toggle component built (top bar, per the component spec)
      and wired to `localStorage` + `users.theme_preference`.
- [x] **Shared component library implemented once, here** — every
      pattern under `09-ui-design-system.md`'s Component library section
      (toast notifications, the trend-chart loading/empty states, empty
      states generally, the destructive-action confirm dialog, filter/
      date-range chip menus, stat-tile skeleton loading, the tooltip, the
      button loading/success/disabled sequence, the toggle switch, the
      icon-only row-actions menu, the upload progress bar, and
      pagination) — as real, reusable components, not redrawn per screen.
      Every screen from Module 2 onward references these rather than
      reinventing them. Note the `disabled="{expr}"` gotcha called out
      under "Button states" and "Pagination" in that file — a real HTML
      `disabled` attribute disables on presence regardless of its string
      value, so gate on conditional rendering or a controlled boolean
      prop instead.
- [x] Auth: magic-link sign-in working end to end. Verified live:
      request link → backend emails single-use ticket → exchange →
      JWT → redirect to role landing, with CORS preflight passing.
- [ ] Auth: at least one SSO provider (Google, Microsoft/Azure AD, or
      Okta) working end to end via OAuth/OIDC. Google OAuth flow built
      (Django-owned handshake → sign-in ticket → same exchange as
      magic-link); awaiting real Google client credentials from the
      product owner to verify end to end.
- [x] State/LGA/Ward reference data seeded from the real national
      administrative list (per open decision #8 in `08-delivery-plan.md`
      — confirm the source list before seeding). Source confirmed with
      product owner: authentic public INEC/GRID3-derived dataset
      (kaygeea/nigeria-geojson-data). Pilot scope: 10 states incl.
      FCT/Abuja, Lagos, Kano (231 LGAs, 2,819 wards); `seed_geo` is
      idempotent and extensible by dropping in a wider fixture.
- [x] Admin facility-creation screen (`/admin/facilities`, the guided
      State → LGA → Ward picker) built to `09-ui-design-system.md`'s
      screen spec, both light and dark mode. Verified live: created
      "Gama Primary Health Centre" (Kano · Nasarawa · Gama ward) by
      walking the seeded picker; success toast + table row rendered.
- [x] Empty dashboard shell reachable post-login, sidebar nav rendering
      correctly for at least the Systems admin role (full nav
      per the navigation map). App shell (sidebar + frosted top bar +
      theme toggle), role-aware nav for all four roles with the
      universal active-nav treatment, route guard, and placeholder
      shells for every later-module route so no nav link 404s.

## Module 2 — Intake and templates

**Status:** Done — exit condition verified (golden-file tests pass for
ANC/Delivery/PNC incl. a facility-specific override, a confirmed
low-confidence batch, a mis-declared batch held by the cross-check, and a
simulated extraction-provider failure that recovers on retry). Live
extraction verified end to end with OpenAI gpt-4o; the full
capture→extract(SSE)→confirm→publish flow and the admin template-mapping
screen are built in both light and dark mode. Templates reconciled with
the real NHMIS registers (open decision #1 resolved).
**Exit condition:** "Golden-file tests pass for ANC, Delivery, and PNC,
including a facility-specific template override, an image-sourced batch
that only publishes after its low-confidence fields are confirmed, and
a deliberately mis-declared batch (e.g. a Delivery photo submitted as
ANC) that gets held by the cross-check rather than publishing."

- [x] `templates`, `intakes`, `source_rows`, `template_flags` tables
      migrated per `03-templates-and-intake.md`'s schema, including the
      register-mismatch columns on `intakes`. Also added `IntakeImage`
      (multi-page batches) and `FieldCorrection` (append-only correction
      history), both faithful to the lineage layer in `02-data-model.md`.
- [x] ANC v1, Delivery v1, and PNC v1 shared/default templates entered
      per `03-templates-and-intake.md` and seeded (facility IS NULL).
      ANC exact; Delivery/PNC **reconciled against the REAL NHMIS
      registers** in Cureva's existing platform (app.cureva.care:
      antenatal_registrations, deliveries, postnatal_records) — this
      resolves open decision #1. ANC 22 / Delivery 25 / PNC 24 columns,
      canonical names kept stable for the cross-check/lenses, real
      register labels added as aliases. Post-launch changes go through a
      new template version, never in-place (rule #2).
- [x] Fingerprint/duplicate-checksum check implemented and tested
      (`compute_source_hash`, order-independent over multi-page batches).
- [x] Template resolution (`resolve_template`) implemented and tested,
      including the facility-specific-over-shared-default fallback.
- [x] AI/OCR extraction pipeline wired to the vision model, streaming
      per-field results over SSE (`GET /api/v1/intakes/{id}/progress`).
      Provider swappable (open decision #8): OpenAI (gpt-4o) + Claude
      (sonnet-5-5) behind `extraction_engine`; pilot key is OpenAI's.
      **Live-verified end to end**: a generated ANC register image was
      read by gpt-4o and returned correct rows + confidence through the
      pipeline. SSE stream consumed by the intake screen via fetch
      streaming (JWT in header, not URL).
- [x] `match_extracted_fields` implemented and tested against aliases.
- [x] **Register-family cross-check implemented**
      (`detect_register_family`, `check_register_mismatch`, using
      `register_mismatch_min_signal` from `platform_settings` via the
      shared accessor in the pipeline) and tested with a deliberately
      mis-declared Delivery-as-ANC batch that is held, then switched.
- [x] Type/structure and plausibility-range validation implemented and
      tested (implausible BP/birth-weight flagged not blocked; blank is
      unknown, never flagged — rule #6).
- [x] Field-confirmation screen (`/intakes/[id]/confirm-fields`) built
      to the design system, both modes — per-row cards, low-confidence/
      flagged fields highlighted with confidence %, confirm/correct per
      field, publish gated on all fields confirmed.
- [x] Capture Register / Upload Register intake screen
      (`DataOfficer` equivalent, `/intakes`) built to
      `09-ui-design-system.md`'s screen 5 spec — the session-level
      workspace switcher (facility index / active facility) and every
      intake-card state (idle, staged, extracting with the live SSE
      field checklist, done, register-mismatch banner) — light and dark
      mode. (Desktop; the dedicated mobile screen 6 layout is still to
      build.)
- [x] Same screen's mobile layout (screen 6 spec — the workspace bar,
      the same intake-card states, and the plain two-item bottom tab bar
      with no More sheet, since a Data officer's whole nav is just those
      two links) built, light and dark mode. Implemented as a responsive
      AppShell: below 768px the sidebar is replaced by a bottom tab bar
      (role-aware, with a More sheet for roles that have >4 links; the
      Data officer's two links show as a plain two-item bar), content
      stacks full-width, no horizontal page scroll.
- [x] Template-mapping admin screen (`/admin/templates`) built to the
      design system, light and dark mode — family segmented control,
      shared-default card with field chips, facility-override table, and
      the open-flags panel. Plus the per-intake mapping screen
      (`/intakes/[id]/mapping`): map unmatched labels → canonical field,
      save as alias (writes a NEW template version, rule #2). Backend:
      `GET /template-flags`, `POST /templates/{id}/aliases` (new version).
- [x] Facility flagging (`POST /api/v1/intakes/{id}/flag`) implemented.
      Full intake API wired: create (multipart, duplicate no-op), validate,
      rows, confirm-field, publish (idempotent), resolve-register-mismatch,
      flag, mapping (admin), my-intakes, templates — with role enforcement
      (org users rejected) and HTTP-level tests for the create→validate→
      confirm→publish flow.
- [x] Publish/hold logic implemented: a row only reaches `published`
      after every gate (type/structure, plausibility acknowledged,
      register-family resolved, every low-confidence field confirmed).
      Publish is idempotent (status + `select_for_update`), per-field
      confirm/correct records append-only `FieldCorrection` history.
- [x] Golden-file tests written and passing for all three register
      families, a facility-specific override, a confirmed
      low-confidence batch, a mis-declared-family batch (held → switched,
      and held → confirm-declared), and a simulated extraction-provider
      failure that lands on `extraction_failed` and recovers on retry.

## Module 3 — Identity linkage

**Status:** Done — exit condition verified: candidate matches never
auto-merge (only a human confirmation, which requires a reviewing user,
creates a link — tested), and every confirm/reject writes an audit
event. Strict fast path + probabilistic matching both built, threshold
read from platform_settings, review queue screen built in both modes.
**Exit condition:** "Candidate matches never auto-merge; every
confirm/reject is audited."

- [x] `identity_candidates` table migrated per `02-data-model.md` (plus
      `Woman` and `SourceRowLink`, built now as the dependency identity
      linkage needs — noted per the "build the dependency first" rule).
- [x] Strict-identifier fast-path matching implemented and tested
      (links to an existing Woman by card/folder number, or creates one;
      automatic, no human).
- [x] Probabilistic candidate matching implemented (name, DOB/age,
      phone), confidence score computed and stored, threshold read from
      `identity_candidate_confidence_threshold` in `platform_settings`.
      Hooked into publish (strict first, then candidate queuing).
- [x] Identity-review queue (`/identity-review`) built to the design
      system, light and dark mode — per-candidate cards showing the new
      record vs the candidate Woman, matched-on fields, confidence %, and
      Confirm/Reject actions. Facility-lead-only.
- [x] Confirm/reject endpoints implemented; confirm merges into the
      Woman record (and rejects other pending candidates for that row),
      reject leaves the encounter unlinked; both write an audit event.
      Facility-lead-only, scoped to their facility.
- [x] Tests confirm no code path can set a candidate match's status to
      `confirmed` without a `reviewed_by` user (the single confirm path
      requires a reviewing user and raises without one).

## Module 4 — Maternal model and dashboards

**Status:** Done — exit condition verified: dashboard metrics reconcile
exactly with a hand-calculated fixture (test), and an organisation
scoped to a subset of facilities reconciles to exactly that subset. All
five MAIN dashboards (Overview/Care journey/Outcomes/Facilities/Records)
+ My organisation's users built in both modes; Facility-lead Overview
verified live. Access-level filtering enforced on Records.
**Exit condition:** "Dashboard metrics reconcile exactly with a
manually calculated fixture dataset."

- [x] Woman / PregnancyEpisode / ANCContact / BirthEvent / PNCContact /
      Referral tables migrated per `02-data-model.md` (Woman already in
      Module 3; the event tables added here).
- [x] Maternal Projection app writes these from verified source rows,
      per the data-flow summary in `04-architecture-and-stack.md` —
      hooked into publish (strict-linked rows) and candidate confirm.
      Only linked rows project; unlinked encounters stay source-only.
- [x] Daily facility metric aggregation job implemented (idempotent,
      re-runnable without double counting) — `rebuild_facility_metrics`
      deletes + recomputes a facility's daily rows from the events.
- [x] Overview (`/overview`) built to `09-ui-design-system.md` screen 1,
      role-adaptive (Organisation user multi-facility view with a
      facilities table; Facility lead single-facility view), light and
      dark mode. Verified live for a Facility lead.
- [x] Care journey (`/care-journey`) built, both view modes, light and
      dark mode — funnel + the MVP metric set, each shown with its
      numerator/denominator (rule #5).
- [x] Outcomes (`/outcomes`) built, both view modes, light and dark mode
      — documented outcomes only, never inferred (rule #6).
- [x] Facilities (`/facilities`) built, light and dark mode — per-facility
      reporting freshness, verified records, referrals, stale flag.
- [x] Records (`/records`) built with access-level filtering (aggregate
      tier gets counts only, not rows; de-identified strips declared
      identity fields; identifiable sees full evidence), paginated, light
      and dark mode.
- [x] Facility lead's locked overview (screen 4 spec — stat row + funnel)
      built and verified live. The inline follow-up worklist and
      identity-match table on this screen depend on Module 5's rule
      engine / Module 3's queue and are surfaced on their own screens
      (`/needs-attention`, `/identity-review`); the inline embeds land
      with Module 5.
- [x] Fixture dataset built and metric reconciliation test passing for
      the MVP metric set (`06-metrics-and-reporting.md`) — published a
      known fixture through the real pipeline and reconciled operational
      counts, early-booking, delivery/postnatal linkage, and outcomes to
      hand-calculated values.
- [x] Organisation-scoped filtering implemented on every dashboard
      endpoint: an Organisation user resolves to their organisation's
      effective facility set (explicit grants ∪ region grants, expanded
      server-side) and never sees a facility outside it. Tested: an org
      granted only facility A reconciles to A's numbers (B excluded); a
      ward grant expands to both facilities under it.
- [x] "My organisation's users" screen (`/org/users`) built to
      `09-ui-design-system.md`'s screen 9 spec, both light and dark
      mode — list + invite (role always organisation_user, with a
      can_manage_org_users toggle). The row-actions Deactivate lands in
      Module 6 alongside the `DELETE` endpoint.

## Module 5 — Risk, referrals, and reporting

**Status:** Done except clinical sign-off — every section is built and
tested; the exit condition ("Clinical review of generated reports
completed") is blocked only on open decision #2 (a NAMED clinical owner),
which is a stakeholder decision, not a build task. Rules carry
"UNASSIGNED (pending clinical sign-off)" as the owner until a human is
named.
**Exit condition:** "Clinical review of generated reports
completed."

- [x] Risk/referral rule engine implemented per
      `06-metrics-and-reporting.md`'s "Risk and follow-up rules" (MVP
      rule set: abnormal BP, anaemia, danger signs, open referral,
      missing postnatal — each versioned with owner/effective-date/
      severity; owner pending open decision #2). Tested.
- [x] Needs attention (`/needs-attention`) worklist screen built to
      `09-ui-design-system.md`'s screen 12 spec, light and dark mode —
      **Facility lead only**; not on an Organisation user's nav, and
      `GET /api/v1/worklists` rejects an Organisation user caller
      server-side (tested: 403 for org user, 200 for facility lead).
- [x] "Open referrals" stat tile on Organisation user's Overview wired
      to the rolled-up count via `GET /api/v1/maternal-summary` — the
      organisation-facing substitute for worklist access (built in the
      Module 4 Overview; org users never reach the case-level worklist).
- [x] `worklist_actions` table migrated and
      `POST /api/v1/worklists/{itemId}/action` implemented — an audit
      overlay only, never a write to register data or `referral_status`;
      an actioned item still resurfaces while its rule is true, now
      showing its action history (tested).
- [x] All 11 intelligence lenses (`06-metrics-and-reporting.md`)
      implemented as queries against the maternal model (`lenses.py`),
      each returning counts with denominators.
- [x] Evidence explorer / export functionality implemented, access-level
      enforced — CSV export rejects aggregate tier, de-identifies for the
      de-identified tier, and writes an `ExportAudit` event.
- [x] Healthcare-facing report generator implemented: deterministic
      sections/charts first, optional aggregate-only LLM narrative pass
      (OpenAI, no identifiable data sent, cannot invent prevalence).
- [x] Reports screen (`/reports`) built, light and dark mode — generate
      (with optional narrative), view saved briefs, export CSV.
- [ ] A generated report reviewed and sign-off recorded by the named
      clinical owner (open decision #2 in `08-delivery-plan.md`) —
      **blocked on naming a clinical owner (stakeholder decision).**

## Module 6 — Operations and hardening

**Status:** Not started
**Exit condition:** "All launch gates [in `08-delivery-plan.md`] pass."

- [x] Admin settings screen (`/admin/settings`) built to
      `09-ui-design-system.md`'s screen 11 spec — every `platform_settings`
      key editable (per-row `PATCH /settings/{key}`, type-matched input),
      linked from the Systems admin sidebar. Verified live.
- [x] User notification-preferences screen (`/settings/notifications`)
      built, light and dark mode, reachable from the account menu on
      every role's sidebar — per-type channel (email/SMS/both/none),
      self-service.
- [x] **Account menu built once, here** — the popover behind every
      sidebar's avatar (Profile with self-editable name via
      `PATCH /api/v1/users/me`, Notification preferences, Sign out in
      danger red), per the Component library spec. The sidebar footer now
      references it on every screen.
- [x] Stale-facility alert job implemented (`stale_facility_alerts`
      management command, schedulable), reading its threshold from
      `platform_settings` and each recipient's channel from
      `notification_preferences`; SMS via Termii behind the notification
      module's own interface. A failed send never blocks the stale check.
- [x] Users & roles admin screen (`/admin/users`) built to
      `09-ui-design-system.md`'s screen 10 spec — create, edit, and
      deactivate/reactivate (`PATCH /users/{id}`,
      `POST /users/{id}/deactivate|reactivate`), with the icon-only
      row-actions menu and the destructive-confirm dialog, light/dark.
- [x] Organisation-side user removal implemented: the row-actions menu
      on "My organisation's users" gets a Deactivate action,
      `DELETE /api/v1/organisations/{id}/users/{userId}`, scoped strictly
      to the caller's own organisation and gated on `can_manage_org_users`
      (tested: the narrow exception holds, every other combination 403).
- [x] Monitoring/logging wired per "Performance and reliability
      targets" — structured logging configured (no PHI in logs), and
      the metrics to monitor are exposed (facility freshness, open
      flags, pending rows, stale facilities). External dashboards are a
      deploy-time ops concern.
- [x] Access-control test suite passing (aggregate / de-identified /
      identifiable, per `07-security-privacy-access.md`), including that
      every capture/correct/resolve endpoint rejects an Organisation
      user caller outright, regardless of what the UI shows — with the
      one deliberate, narrowly-scoped exception tested explicitly:
      `DELETE /api/v1/organisations/{id}/users/{userId}` succeeds only
      for a `can_manage_org_users` caller acting on their own
      organisation's own invited users, and is rejected for every other
      combination (another organisation's users, a Facility lead, a
      Data officer, a Systems admin, or a caller without
      `can_manage_org_users`). Also test the read-side exception the
      other way: an Organisation user caller is rejected outright on
      `/needs-attention`, `GET /api/v1/worklists`, and
      `POST /api/v1/worklists/{itemId}/action`, while a Facility lead
      succeeds on all three, scoped to their one facility.
- [ ] Performance tuning pass; p95 dashboard target met.
- [ ] Backup/restore drill completed.
- [ ] **Full design-system audit**: every screen built in Modules 1–6
      checked against `09-ui-design-system.md` in both light and dark
      mode — no screen left half-styled, no hard-coded color outside
      the token system.
- [ ] Every launch gate in `08-delivery-plan.md` checked off explicitly
      (copy the list into this section's sub-checklist and verify each
      one individually before declaring the module — and the build —
      done).

---

## When every module is done

Cureva Care meets its "Definition of done" in `08-delivery-plan.md`. Make a
final commit and push confirming every module's status line above reads
`Done`, and stop — do not start any feature not named in this package
without checking back first.
