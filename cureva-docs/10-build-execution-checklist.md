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

**Status:** In progress
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
      ANC exact; Delivery/PNC built out from the documented key + lens +
      signature fields. **Open decision #1: final Delivery/PNC column
      lists still to be confirmed against the real national registers**
      — a new template version when they are, never an in-place edit.
- [ ] Fingerprint/duplicate-checksum check implemented and tested.
- [ ] Template resolution (`resolve_template`) implemented and tested,
      including the facility-specific-over-shared-default fallback.
- [ ] AI/OCR extraction pipeline wired to the vision model, streaming
      per-field results over SSE (`GET /api/v1/intakes/{id}/progress`).
- [ ] `match_extracted_fields` implemented and tested against aliases.
- [ ] **Register-family cross-check implemented**
      (`detect_register_family`, `check_register_mismatch`, using
      `register_mismatch_min_signal` from `platform_settings`) and
      tested with a deliberately mis-declared batch per family.
- [ ] Type/structure and plausibility-range validation implemented.
- [ ] Field-confirmation screen (`/intakes/[id]/confirm-fields`) built
      to the design system, both modes.
- [ ] Capture Register / Upload Register intake screen
      (`DataOfficer` equivalent, `/intakes`) built to
      `09-ui-design-system.md`'s screen 5 spec — the workspace switcher
      (no facility active / facility active) and every intake-card state
      within it (idle, staged, extracting, done, register-mismatch
      banner) — light and dark mode.
- [ ] Same screen's mobile layout (screen 6 spec — the workspace bar,
      the same intake-card states, and the plain two-item bottom tab bar
      with no More sheet, since a Data officer's whole nav is just those
      two links) built, light and dark mode.
- [ ] Template-mapping admin screen (`/admin/templates`) built to the
      design system, light and dark mode.
- [ ] Facility flagging (`POST /api/v1/intakes/{id}/flag`) implemented.
- [ ] Publish/hold logic implemented: a row only reaches `published`
      after every gate (type/structure, plausibility acknowledged,
      register-family resolved, every low-confidence field confirmed).
- [ ] Golden-file tests written and passing for all three register
      families, a facility-specific override, a confirmed
      low-confidence batch, and a mis-declared-family batch.

## Module 3 — Identity linkage

**Status:** Not started
**Exit condition:** "Candidate matches never auto-merge; every
confirm/reject is audited."

- [ ] `identity_candidates` table migrated per `02-data-model.md`.
- [ ] Strict-identifier fast-path matching implemented and tested.
- [ ] Probabilistic candidate matching implemented (name, DOB, facility,
      phone), confidence score computed and stored, threshold read from
      `identity_candidate_confidence_threshold` in `platform_settings`.
- [ ] Identity-review queue (`/identity-review`) built to the design
      system, light and dark mode.
- [ ] Confirm/reject endpoints implemented; confirm merges into the
      Woman record, reject leaves the encounter unlinked; both write an
      audit event.
- [ ] Tests confirm no code path can set a candidate match's status to
      `confirmed` without a `reviewed_by` user.

## Module 4 — Maternal model and dashboards

**Status:** Not started
**Exit condition:** "Dashboard metrics reconcile exactly with a
manually calculated fixture dataset."

- [ ] Woman / PregnancyEpisode / ANCContact / BirthEvent / PNCContact /
      Referral tables migrated per `02-data-model.md`.
- [ ] Maternal Projection app writes these from verified source rows,
      per the data-flow summary in `04-architecture-and-stack.md`.
- [ ] Daily facility metric aggregation job implemented (idempotent,
      re-runnable without double counting).
- [ ] Overview (`/overview`) built to `09-ui-design-system.md` screen 1,
      both the full multi-facility view and the facility-locked view
      for Data officer/Facility lead, light and dark mode.
- [ ] Care journey (`/care-journey`) built, both view modes, light and dark
      mode.
- [ ] Outcomes (`/outcomes`) built, both view modes, light and dark
      mode.
- [ ] Facilities (`/facilities`, and `/admin/facilities`'s table) built,
      light and dark mode.
- [ ] Records (`/records`) built with access-level filtering, light and
      dark mode.
- [ ] Facility lead's locked overview (screen 4 spec — stat row,
      funnel, follow-up worklist, inline identity-match table) built,
      light and dark mode.
- [ ] Fixture dataset built and metric reconciliation test passing for
      every metric in the MVP metric set (`06-metrics-and-reporting.md`).
- [ ] Organisation-scoped filtering implemented on every dashboard/report
      endpoint: an Organisation user/viewer resolves to their
      organisation's effective facility set (explicit grants union
      region-level grants) and never sees a facility outside it. Tested
      against the same fixture dataset, granting a test organisation a
      subset of the fixture's facilities and confirming its numbers
      reconcile to exactly that subset.
- [ ] "My organisation's users" screen (`/org/users`) built to
      `09-ui-design-system.md`'s screen 9 spec, both light and dark
      mode.

## Module 5 — Risk, referrals, and reporting

**Status:** Not started
**Exit condition:** "Clinical review of generated reports
completed."

- [ ] Risk/referral rule engine implemented per
      `06-metrics-and-reporting.md`'s "Risk and follow-up rules" (MVP
      rule set, each versioned with owner/effective-date/severity).
- [ ] Needs attention (`/needs-attention`) worklist screen built to
      `09-ui-design-system.md`'s screen 12 spec, light and dark mode —
      **Facility lead only**; not on an Organisation user's nav, and
      `GET /api/v1/worklists` rejects an Organisation user caller
      server-side.
- [ ] "Open referrals" stat tile on Organisation user's Overview
      (`09-ui-design-system.md` screen 1) wired to the rolled-up Needs
      attention count via `GET /api/v1/maternal-summary` — the
      organisation-facing substitute for worklist access, per screen 12.
- [ ] `worklist_actions` table migrated (`02-data-model.md`) and
      `POST /api/v1/worklists/{itemId}/action` implemented — an audit
      overlay only, never a write to the underlying register data or
      `referral_status`; a worklist item still resurfaces if its rule
      still evaluates true after a later intake.
- [ ] All 11 intelligence lenses (`06-metrics-and-reporting.md`)
      implemented as queries/views against the maternal model.
- [ ] Evidence explorer / export functionality implemented, access-level
      enforced.
- [ ] Healthcare-facing report generator implemented: deterministic
      charts first, optional aggregate-only LLM narrative pass.
- [ ] Reports screen (`/reports`) built, light and dark mode.
- [ ] A generated report reviewed and sign-off recorded by the named
      clinical owner (open decision #2 in
      `08-delivery-plan.md`).

## Module 6 — Operations and hardening

**Status:** Not started
**Exit condition:** "All launch gates [in `08-delivery-plan.md`] pass."

- [ ] Admin settings screen (`/admin/settings`) built to
      `09-ui-design-system.md`'s screen 11 spec — every `platform_settings`
      key editable, linked from Systems admin's sidebar (it wasn't,
      before the Roles & Operations review caught it), light and dark
      mode.
- [ ] User notification-preferences screen (`/settings/notifications`)
      built, light and dark mode, reachable from the account menu (see
      "Account menu" in the Component library) on every role's sidebar
      — not just built, actually linked to.
- [ ] **Account menu built once, here** — the popover behind every
      sidebar's avatar (Profile with self-editable name via
      `PATCH /api/v1/users/me`, Notification preferences, Sign out), per
      the Component library spec. Every screen from here on references
      it rather than rebuilding the sidebar footer per screen.
- [ ] Stale-facility alert job implemented, reading its threshold from
      `platform_settings` and each recipient's channel from
      `notification_preferences`.
- [ ] Users & roles admin screen (`/admin/users`) built to
      `09-ui-design-system.md`'s screen 10 spec — create, **and now also
      edit and deactivate/reactivate** an existing user
      (`PATCH /api/v1/users/{id}`, `POST /api/v1/users/{id}/deactivate`,
      `POST /api/v1/users/{id}/reactivate` — this was create-only until
      the Roles & Operations review), light and dark mode.
- [ ] Organisation-side user removal implemented: the row-actions menu
      on "My organisation's users" (`09-ui-design-system.md` screen 9)
      gets a Deactivate action, `DELETE
      /api/v1/organisations/{id}/users/{userId}`, scoped strictly to the
      caller's own organisation and gated on `can_manage_org_users`.
- [ ] Monitoring/logging wired per "Performance and reliability
      targets" in `04-architecture-and-stack.md`.
- [ ] Access-control test suite passing (aggregate / de-identified /
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
