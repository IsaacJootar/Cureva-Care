# Delivery Plan

## Build phases

Phased for clarity and testability, not to fit a fixed human sprint
calendar — see `00-START-HERE.md`. Each phase should be fully working and
tested before moving to the next.

| Phase | Output | Exit condition |
|---|---|---|
| 1. Foundations | Django project structure (Identity/Access, Register Intake, Maternal Projection, Intelligence, Reporting apps), Postgres schema — including `organisations`, `organisation_facility_access`, and `users` (see `02-data-model.md`) — Next.js project scaffolded with Tailwind and the shared design system, auth (magic-link + SSO) working end to end, State/LGA/Ward reference data seeded, the admin facility-creation screen (guided State → LGA → Ward picker) built, and the admin organisation-management screen (`/admin/organisations`) built | A user can log in through either path, reach an empty dashboard shell, a Systems admin can create a facility by walking the seeded State → LGA → Ward picker, and a Systems admin can create an organisation and grant it access to at least one facility |
| 2. Intake and templates | Full intake pipeline: fingerprinting, per-facility template resolution and matching, the template-mapping admin screen, facility flagging, plausibility checks, publish/hold logic, AI/OCR image intake with per-field confidence and the field-confirmation screen, the register-family cross-check and its confirm/switch resolution screen, extraction-failure retry handling | Golden-file tests pass for ANC, Delivery, and PNC, including a facility-specific template override, an image-sourced batch that only publishes after its low-confidence fields are confirmed, a deliberately mis-declared batch (e.g. a Delivery photo submitted as ANC) that gets held by the cross-check rather than publishing, and a simulated extraction-provider failure that lands on `extraction_failed` and recovers via retry rather than being lost |
| 3. Identity linkage | Strict-identifier fast path, probabilistic candidate matching with confidence scoring, the identity-review queue and confirm/reject flow | Candidate matches never auto-merge; every confirm/reject is audited |
| 4. Maternal model and dashboards | Woman/Episode/Contact/Event/Referral projection, Overview, Care journey, Outcomes, Facilities, Records views, organisation-scoped filtering on all of the above | Dashboard metrics reconcile exactly with a manually calculated fixture dataset, and an organisation account, when pointed at the same fixture data, sees metrics that reconcile to exactly its granted facilities — no more, no less |
| 5. Risk, referrals, and reporting | Full risk/referral rule engine, worklists, exports, the healthcare-facing report generator (deterministic charts + optional LLM narrative) | Clinical review of generated reports completed |
| 6. Operations and hardening | Platform configuration module (`platform_settings` + per-user `notification_preferences`, the `/admin/settings` and `/settings/notifications` screens), stale-facility alerting reading its threshold and every recipient's channel from that module, monitoring/logging, access-control tests, performance tuning, backup/restore drill | All launch gates below pass |

## Team

| Role | Focus |
|---|---|
| Product/implementation lead | Scope, workflow correctness, acceptance, facility feedback |
| Backend engineer (Python/Django) | Intake, lineage, identity linkage, maternal model, metrics, API |
| Frontend engineer (Next.js/React/Tailwind) | The full UI — dashboards and every admin screen, one consistent design system |
| Maternal-health clinical lead | Data dictionary, rule approval, interpretation, safety review |
| QA/data reviewer | Golden files, reconciliation, access-control verification |

## Launch gates

- At least one approved sample from each ANC, Delivery, and PNC register
  version in use, including any facility-specific templates.
- 100% of published fields resolve to a source row and intake.
- Exact re-import produces zero duplicate rows, corrections, or aggregate
  counts.
- No pending or rejected row appears in intelligence, reports, or verified
  exports.
- No candidate identity match is ever merged without a recorded human
  confirmation.
- No intake whose extracted fields don't match its declared register
  family ever reaches field confirmation or publish without a recorded
  human resolution (confirm or switch) — verified with a batch from each
  of the other two families deliberately submitted under the wrong one.
- All maternal metrics reconcile against a manually calculated acceptance
  dataset.
- Service-date filters work independently of source receipt/publication
  dates.
- Identity access, search, and export actions produce auditable events.
- No PHI appears in logs, LLM prompts, or aggregate-only reports.
- The dashboard meets the agreed p95 performance target and survives
  partial panel failure.
- An organisation account never sees a facility outside its configured
  grant (facility- or region-level), and every capture/correct/resolve
  endpoint rejects an organisation-side caller outright — verified by
  test, not just by the UI hiding the relevant screens.
- Stale-facility alerts fire correctly at the configured threshold
  (default 14 days) and reach each recipient only on their own configured
  channel(s).
- No alert threshold, confidence threshold, or notification channel is
  hard-coded anywhere in application code — every one is read from
  `platform_settings` or a user's `notification_preferences` at runtime,
  editable by a Systems admin (or, for a user's own notification
  channel, by that user) without a code change. Verified by code review
  and by changing a setting in a test environment and confirming the
  behaviour changes with no deploy.
- No AI-extracted image-intake row ever reaches "published" with an
  unconfirmed low-confidence field — verified by test, not just by design.
- A restore test and an incident-response tabletop exercise have been
  completed.
- Every screen in the product — dashboard and admin alike — uses the same
  design system; no Django-rendered or default-styled page is reachable by
  any user.

## Product success measures

| Measure | Target |
|---|---|
| Verified batch turnaround | Reviewed batch visible in intelligence within 5 minutes |
| Lineage coverage | 100% of published records linked to source |
| Duplicate prevention | Zero duplicates from repeated submission of the same file |
| Metric reconciliation | 100% match on the acceptance dataset |
| Facility reporting visibility | Every expected facility shown, including those with no data |
| Identity-match discipline | Zero unconfirmed candidate matches counted as linked |
| Actionability | A Facility lead or Organisation user can identify and assign follow-up from one workspace |

## Decisions still open with stakeholders

1. Final, approved ANC/Delivery/PNC column lists for the default templates
   (used to finalize `03-templates-and-intake.md`'s templates).
2. Named clinical owner who approves risk rules, denominators, and
   maternal-care interpretations.
3. Pilot facility list and which roles may see identities at each one.
4. Data retention period, hosting region, and backup/incident obligations
   for maternal records — hosting region specifically should be checked
   against Nigeria's Data Protection Act (NDPA 2023), not chosen on
   cost/performance grounds alone (see `07-security-privacy-access.md`).
5. The confidence-score threshold for surfacing a candidate identity match
   for human review (`identity_candidate_confidence_threshold` in
   `platform_settings`, see `02-data-model.md`) — needs either a
   clinical/data-governance decision or early pilot data to tune sensibly;
   changing it later is a settings edit, not a deploy.
6. The confidence-score threshold for flagging an AI-extracted field for
   mandatory review on image intake (`ai_extraction_confidence_threshold`
   in `platform_settings`, starts at 0.85 — see
   `03-templates-and-intake.md` and `02-data-model.md` — then tune against
   early pilot images, again as a settings edit).
7. Confirm the seed list of States, Local Government Areas, and Wards to
   load before any facility can be created (see `02-data-model.md`'s
   facility administrative hierarchy) — this is reference data, not
   something admins should be typing in by hand at facility-creation time.
8. Confirm the OCR/vision provider before locking in real spend.
   `04-architecture-and-stack.md` names Claude (Anthropic) vision API as
   the pilot default so the build isn't blocked on this — swappable via
   `extraction_engine` if accuracy testing or commercial terms favor a
   different provider. **The SMS provider is no longer open — settled
   on [Termii](https://termii.com/)**, see `04-architecture-and-stack.md`;
   still integrated behind the notification job's own interface so a
   future change stays a one-module swap, not a reason to keep it on
   this list.
9. Dark-mode value for `--cv-button-primary-bg` (see
   `09-ui-design-system.md`'s "Design tokens" and "Component library").
   Light mode is locked at `#111110`, the sidebar's own dark ink — but
   that same value would go nearly invisible against dark mode's
   `#0b0c10` page background. Needs a real dark-mode pairing (most
   likely a light neutral button with dark text, the inverse of light
   mode) signed off before Module 1's design-token work is called done;
   don't guess at build time.

## Principal risks

| Risk | Effect | Mitigation |
|---|---|---|
| Register variation across facilities | Broken mappings, inconsistent metrics | Per-facility templates with golden-file tests per version |
| Upload date used as care date | False trends, misleading reports | `service_date` is first-class; tested on every filter |
| Clinical rule drift | Unsafe or obsolete worklists | Versioned rules with owner, source, effective date, approval |
| Missing data read as normal | False reassurance | Completeness shown separately from clinical status; unknowns labeled |
| Poorly tuned candidate-match confidence threshold | Too many false review prompts, or missed real matches | Monitor confirm/reject rates during pilot; threshold lives in `platform_settings`, not hard-coded, so it's tuned by editing a setting, not shipping code |
| Low AI-extraction accuracy on handwritten registers | Wrong clinical values reach a reviewer as "confident," or reviewers rubber-stamp without really checking | Per-field (not per-row) confidence, tunable threshold, track confirm-vs-correct rates from first pilot images, never let the model self-verify |
| Sensitive data exposure | Harm, legal risk, loss of trust | Least privilege, audit, private storage, no PHI in logs/prompts |
| Inconsistent UI between dashboard and admin tools | Confusing experience, slower adoption | Single Next.js app, one design system, enforced as a launch gate |

## Definition of done

Cureva Care is done when a reviewed maternal register batch — from a facility
using either the shared default template or its own — can be added once,
traced to source, correctly linked to a Woman/Pregnancy episode (via
strict match or a confirmed candidate) or correctly retained as an
unlinked encounter, reflected in service-date intelligence, opened as
evidence by an authorized user, exported under the correct access level,
and summarized in a healthcare-facing brief whose figures reconcile
exactly with the dashboard — all inside one consistent, well-designed
interface.
