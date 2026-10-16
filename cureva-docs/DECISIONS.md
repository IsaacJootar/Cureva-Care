# Cureva Care — build decisions log

A running record of the notable decisions taken while building Cureva Care:
**what** changed, **why**, and **how it's used**. This feeds the eventual usage
document (what we built, the reasoning, and how it's operated). Newest sections
are appended at the bottom.

---

## Platform & environment

- **Database:** PostgreSQL 16 in a Docker container (`cureva-postgres`, host
  port 5434), isolated from the machine's other projects. *Why:* the stack
  locks PostgreSQL and the native EDB installer was CDN-blocked on this network;
  Docker gives real Postgres without touching the existing XAMPP/MySQL. *Used
  by:* the Django backend via `DATABASE_URL`.
- **Object storage:** MinIO (S3-compatible) container for immutable register-
  photo retention. *Used by:* the intake pipeline (`register_intake/storage.py`).
- **Ports:** backend API on **8001**, frontend on **3100** (3000/5432 were
  taken by other local projects).

## Authentication

- **No passwords anywhere** — sign-in is magic-link or SSO only (a locked
  package decision). *Why:* avoids credential storage/rotation; invite-only.
  *Used by:* every user; the magic link (dev) prints to the backend console.
- **Google SSO** built but **deferred** pending real Google client credentials
  (product-owner decision). Magic-link is fully working.
- **Magic-link lifetime/reuse are env-configurable** (`MAGIC_LINK_TTL_MINUTES`,
  `MAGIC_LINK_SINGLE_USE`). *Why:* during hands-on testing a 15-minute,
  single-use link is painful — it expires on the shelf and dies after one
  click. *How used:* **production keeps the secure defaults** (15 min,
  single-use); the local `.env` currently sets a long TTL and
  `SINGLE_USE=False` so one link per role keeps working while we test. These
  must be reset to the defaults before any real deployment — the code defaults
  are already safe; only the local `.env` relaxes them.

## Vision / OCR provider (open decision #8, resolved)

- **OpenAI (gpt-4o) is the active extraction provider**, swappable behind
  `extraction_engine`; Claude vision is also implemented. *Why:* the pilot's
  available API key is an OpenAI one; the architecture always allowed a swap.
  *Used by:* the intake extraction step; verified live end to end.

## Templates (open decision #1, resolved)

- **Delivery and PNC templates reconciled against the real NHMIS registers** in
  Cureva's existing platform (`app.cureva.care`): Delivery expanded to 25
  columns, PNC to 24, ANC kept at 22. *Why:* the package's Delivery/PNC lists
  were abbreviated placeholders. *Used by:* extraction field-matching.

## Clinical governance (open decision #2, pending)

- Risk/referral rules carry owner `UNASSIGNED (pending clinical sign-off)`
  until a clinical owner is named. The "clinical review of reports" launch gate
  stays open until then.

## Identity-matching update (`IDENTITY_MATCHING_UPDATE.md`)

A product-owner spec that strengthens how the system decides "this row belongs
to this woman." Where it conflicts with the numbered docs, it wins.

- **Section A — always-confirm identity fields.** The card/folder number (and
  ANC number) are marked `always_confirm` in the templates. *What:* a human
  must confirm these against the photo before a row can publish, **even when
  the AI is 100% confident**, and they can't be skipped by any bulk action.
  *Why:* AI confidence doesn't mean correct, and these fields decide which
  woman a visit attaches to. *How used:* the field-confirmation screen now
  shows the register photo and badges identity fields "IDENTITY"; the publish
  gate blocks until they're confirmed. Per-facility templates can't turn it off.

- **Section B — a card number needs a second fact.** *What:* a row auto-links
  on a card-number match only if the name is similar enough
  (`identity_strict_name_floor`, 0.60) AND the match is recent
  (`identity_card_reuse_window_days`, 365). Otherwise it goes to the review
  queue with a reason (name conflict / name missing / stale). *Why:* a smudged
  "1047→1041" could silently attach to the wrong woman; the name has to agree.
  *How used:* the identity-review screen shows the reason in plain words. Name
  matching is its own unit-tested module (honorific-stripping, word-order-
  insensitive, Jaro-Winkler for spelling variants). *Note:* when a register
  doesn't capture a name at all, the name check is N/A and we rely on card +
  recency; a strong name match alone (0.55) stays below the 0.75 review
  threshold on purpose, so two women sharing a common name aren't merged.

- **Section C — remember every identifier.** *What:* a `woman_identifiers`
  table holds every card number (per register family), phone, and name spelling
  a woman has used. Confirming a candidate adds the new row's identifiers.
  *Why:* a second pregnancy gets a new card, and ANC/Delivery/PNC are three
  books with three numbers; remembering all of them bridges them. *Note:*
  `stable_identifier` is kept as the woman's primary card (denormalised); the
  identifier history is what matching reads. Phones are never unique and never
  link on their own.

- **Section D — when a new pregnancy starts.** *What:* an ANC row opens a new
  episode if the latest episode already has a recorded outcome before this
  visit, or it's more than `new_episode_gap_days` (300) past the latest booking
  with no outcome; otherwise it attaches to the open episode. A gestational age
  lower than the previous visit is flagged for review, not silently reshuffled.

- **Section E — linking ANC/Delivery/PNC.** *What:* a Delivery/PNC row's ANC
  number is looked up as the strongest cross-register signal; each register's
  own number is stored too. A Delivery attaches to and closes the open episode;
  a PNC attaches to the most recent episode with a delivery on/before its visit.
  The optional `anc_number` field was added to the Delivery and PNC templates
  (`always_confirm`); the fallback (name/age/phone + human confirmation) works
  when a register has no ANC-number column.

- **Section F — out of scope (first release).** No cross-facility matching
  (a woman at a different clinic is a separate woman), no NIN/BVN matching, no
  automatic merging of two existing women. To be stated in the admin docs.
