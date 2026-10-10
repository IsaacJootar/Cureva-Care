# Templates and Intake Matching

## What a "template" is

A template is a stored, versioned definition of what one register page
should contain: every expected field, its likely alternate labels
(aliases), its data type, whether it's required, and which canonical
maternal-model field it maps to. It is not a copy of the paper form
itself — it's structured metadata describing that form, created once by
walking through the physical register and entering its fields. The AI
extraction step (below) is what actually reads a photographed register
page against this definition.

**Templates are per-facility by design, not just a single shared template.**
Even though most facilities use the same national register form, a facility
that uses a different layout — a renamed field, an added field, a
different register version entirely — must not break intake. The system
resolves which template applies to an intake as follows:

1. Look for an active template where `register_family` matches AND
   `facility_id` matches the uploading facility. If found, use it.
2. Otherwise, fall back to the active template where `register_family`
   matches and `facility_id IS NULL` (the shared/default template).
3. If neither exists, the intake cannot proceed — the admin must register a
   template first (for the facility specifically, or as the new default).

This means: most facilities use the shared default and never need their own
template. A facility whose form genuinely differs gets its own
facility-scoped template — created either proactively during onboarding, or
the first time its submission doesn't cleanly match the default (at which
point the admin clones the default into a facility-specific version and
adjusts the fields that differ). Either way, that one facility's
differences never affect matching for any other facility, and the system
never breaks on a layout mismatch — it just asks for a mapping once.

Templates are stored in PostgreSQL. The field definitions themselves live
inside a JSONB column on the row. The database is where the template lives
permanently; the actual extraction and field-matching comparison happens in
application code, each time a register photo is submitted — not inside SQL.

## Database schema

```sql
CREATE TABLE templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    register_family TEXT NOT NULL,        -- 'ANC' | 'Delivery' | 'PNC'
    facility_id     UUID NULL,            -- NULL = shared national template (MVP default)
    version         INT NOT NULL,
    effective_date  DATE NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    schema          JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (register_family, facility_id, version)
);

CREATE TABLE intakes (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id       UUID NOT NULL,      -- chosen by the data officer at the start of this intake, see "Who submits data, and for which facility" below
    submitted_by      UUID NOT NULL REFERENCES users(id), -- the data officer
    register_family   TEXT NOT NULL,       -- the family the data officer declared: 'ANC' | 'Delivery' | 'PNC'
    template_id       UUID NOT NULL REFERENCES templates(id),
    extraction_engine TEXT NOT NULL,       -- e.g. 'vision-ocr-v1' — which model/version ran
    source_hash       TEXT NOT NULL,       -- checksum of the image file(s)
    file_path         TEXT NOT NULL,       -- private object storage path (the register photo)
    batch_period_from DATE NOT NULL,
    batch_period_to   DATE NOT NULL,
    status            TEXT NOT NULL,       -- 'awaiting_confirmation' | 'published' | 'rejected' | 'extraction_failed'
    suspected_register_family TEXT NULL,   -- set by the cross-check below when the extracted fields look like a different family
    register_mismatch_status  TEXT NOT NULL DEFAULT 'not_applicable', -- not_applicable | flagged | confirmed_as_declared | switched
    register_mismatch_resolved_by UUID NULL REFERENCES users(id),
    register_mismatch_resolved_at TIMESTAMPTZ NULL,
    received_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at      TIMESTAMPTZ NULL,
    UNIQUE (facility_id, register_family, source_hash)
);

CREATE TABLE source_rows (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_id             UUID NOT NULL REFERENCES intakes(id),
    row_number            INT NOT NULL,
    raw_payload           JSONB NOT NULL,      -- untouched, exactly as extracted from the image
    normalized            JSONB NULL,          -- cleaned values, alongside raw
    service_date          DATE NULL,
    status                TEXT NOT NULL,       -- 'awaiting_confirmation' | 'verified' | 'rejected'
    flags                 JSONB NULL,          -- plausibility-check warnings
    extraction_confidence JSONB NOT NULL,      -- {"field": 0.0-1.0, ...}, one score per field
    field_image_regions   JSONB NULL,          -- {"field": {crop coords}} for the review UI
    confirmed_by          UUID NULL REFERENCES users(id),
    confirmed_at          TIMESTAMPTZ NULL
);
```

## Template: ANC (v1)

```json
{
  "register_family": "ANC",
  "version": 1,
  "effective_date": "2026-01-01",
  "columns": [
    { "canonical_field": "card_number", "label": "Card/Folder Number", "type": "string", "required": true,
      "aliases": ["Card No", "Folder No", "Unit No", "Card Number"] },
    { "canonical_field": "lmp", "label": "Last Menstrual Period", "type": "date", "required": true,
      "aliases": ["LMP", "Last Menstrual Period", "L.M.P", "LMP Date"] },
    { "canonical_field": "edd", "label": "Expected Delivery Date", "type": "date", "required": false,
      "aliases": ["EDD", "E.D.D", "Expected Delivery Date", "Due Date"] },
    { "canonical_field": "gravida", "label": "Gravida", "type": "integer", "required": true,
      "aliases": ["Gravida", "G", "Grav"] },
    { "canonical_field": "parity", "label": "Parity", "type": "integer", "required": true,
      "aliases": ["Parity", "P", "Para"] },
    { "canonical_field": "gestational_age_weeks", "label": "Gestational Age (weeks)", "type": "integer", "required": false,
      "aliases": ["GA Weeks", "Gestational Age", "GA (wks)"] },
    { "canonical_field": "blood_pressure", "label": "Blood Pressure", "type": "string", "required": false,
      "plausible_range": "systolic 70-260 / diastolic 40-160",
      "aliases": ["BP", "Blood Press.", "Blood Pressure", "B.P"] },
    { "canonical_field": "weight_kg", "label": "Weight (kg)", "type": "decimal", "required": false,
      "plausible_range": "30-160", "aliases": ["Weight", "Weight (kg)"] },
    { "canonical_field": "haemoglobin", "label": "Haemoglobin", "type": "decimal", "required": false,
      "aliases": ["Hb", "Hb g/dl", "Haemoglobin"] },
    { "canonical_field": "genotype", "label": "Genotype", "type": "enum",
      "enum_values": ["AA", "AS", "SS", "AC", "SC", "CC"], "required": false,
      "aliases": ["Genotype", "Geno"] },
    { "canonical_field": "blood_group_rhesus", "label": "Blood Group / Rhesus", "type": "enum",
      "enum_values": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"], "required": false,
      "aliases": ["Blood Group/Rh", "Blood Group", "BG/Rh"] },
    { "canonical_field": "hiv_result", "label": "HIV Test Result", "type": "string", "required": false,
      "aliases": ["HIV", "HIV Result", "HIV Status"] },
    { "canonical_field": "syphilis_result", "label": "Syphilis Test Result", "type": "string", "required": false,
      "aliases": ["VDRL", "Syphilis"] },
    { "canonical_field": "iron_folate_given", "label": "Iron & Folate Given", "type": "boolean", "required": false,
      "aliases": ["Iron/Folate", "Iron and Folate"] },
    { "canonical_field": "tetanus_given", "label": "Tetanus Vaccination", "type": "boolean", "required": false,
      "aliases": ["TT", "Tetanus", "Tetanus Vaccination"] },
    { "canonical_field": "iptp_given", "label": "IPTp (Malaria Prevention) Dose Given", "type": "boolean", "required": false,
      "aliases": ["IPTp", "IPTp Dose", "SP", "SP Dose", "Malaria Prevention", "Malaria Prophylaxis"] },
    { "canonical_field": "next_appointment", "label": "Next Appointment Date", "type": "date", "required": false,
      "aliases": ["Next Appt", "Next Appointment", "Return Date"] }
  ]
}
```

## Template: Delivery (v1) — abbreviated

Same structure as ANC. Key fields: `card_number`, `delivery_date`,
`delivery_place`, `mode_of_delivery` (enum: SVD/CS/Assisted),
`attendant_category`, `maternal_outcome`, `baby_outcome`, `baby_sex`,
`birth_weight_kg` (plausible range 0.5–6.0), `still_birth`,
`referral_status`. Build out the full column list the same way as ANC,
against your actual national delivery register.

## Template: PNC (v1) — abbreviated

Same structure. Key fields: `card_number`, `visit_date`, `delivery_date`,
`days_postpartum`, `subject` (mother/newborn), `maternal_assessment`,
`newborn_assessment`, `feeding_status`, `danger_signs`, `family_planning`,
`visit_outcome`, `referral_status`.

## Template resolution

```python
def resolve_template(db, register_family: str, facility_id: str) -> dict:
    template = db.templates.find_active(
        register_family=register_family, facility_id=facility_id
    )
    if template is None:
        template = db.templates.find_active(
            register_family=register_family, facility_id=None
        )
    if template is None:
        raise NoTemplateRegistered(register_family, facility_id)
    return template
```

## Who submits data, and for which facility

**Data officers are Cureva Care's own internal staff, not hospital
employees.** Unlike a Facility lead, a data officer's user account has
no `facility_id` — they are not assigned to one facility (see
"Roles, organisations, and users" in `02-data-model.md`). Instead, a
Data officer works inside a **session-level workspace switcher**: no
facility is selected by default (the sidebar reads "No facility
selected"), and opening `/intakes` with nothing chosen shows a facility
index — a single search field over name/LGA/state — instead of the
intake card. Selecting a result scopes the *entire* screen to that
facility (stat tiles, the intake card, intake history) until the officer
taps "Switch facility" again (in the sidebar badge or the top bar). Only
once a facility is active do Capture Register / Upload Register become
available. This is deliberately **not** the hierarchical State → LGA →
Ward picker used for one-off setup tasks like `/admin/facilities` (see
"Facility administrative hierarchy" in `02-data-model.md`) — a Data
officer switches facilities many times a day, so it's one flat search
field, not a multi-step drill-down. See "Workspace switcher (Data
officer)" in `09-ui-design-system.md`'s Component library for the full
spec, and screens 5–6 there for how it looks on desktop and mobile.

This means one data officer might submit a Delivery batch for a
facility in Kano in the morning and an ANC batch for a facility in
Lagos in the afternoon — nothing restricts which facility they can
submit for, and every intake records exactly who submitted it
(`intakes.submitted_by`) and which facility they chose
(`intakes.facility_id`), so nothing about "who submitted this, and for
where" is ever ambiguous even though the officer isn't facility-locked.

## Intake: capture or upload a register photo

**There is one intake channel: a photographed register page.** Cureva Care has
no CSV or Excel upload anywhere in the product. Once a data officer has
chosen which facility a batch is for (above), they either:

- **Capture Register** — photographs the register page live, using this
  device's camera, or
- **Upload Register** — uploads an existing photo from storage.

These are two entry points into the exact same pipeline — the system only
ever sees an image file, and it makes no difference whether that photo was
just taken or was taken earlier on another device and transferred, synced,
or emailed over. Multi-page batches are multiple images against one intake.
Basic client-side checks (blur, crop, lighting) prompt a retake or a
different file before submission, to cut down on unusable images reaching
the extraction model at all.

Capturing or uploading images only stages them — it does not start
extraction by itself. Once a data officer has all the pages for this
batch staged (one page or several), they review the thumbnails — each
with a **Remove** action to drop a bad shot and retake or re-upload it
before committing anything — and press a single **Extract** action to
commit the batch and kick off processing. This is a deliberate two-step
split: staging first means a multi-page register can be assembled and
checked before anything is sent for extraction, and pressing Extract is
the moment the live "scanning and matching" sequence described below
begins.

## Extraction and field matching

The image is sent to a vision-capable model, prompted with the resolved
template's field list (canonical fields, labels, aliases, types, plausible
ranges). The model returns one row per register line, with a value for
each field it could read. **Default provider for the pilot: the Claude
(Anthropic) vision API**, called from the Django backend — a named,
concrete choice so this is buildable, not a placeholder decision left for
later. It sits behind the `extraction_engine` field on `intakes` (see the
schema above) specifically so it can be swapped for a purpose-built
OCR/forms product without a data-model change, if accuracy testing
against real pilot register photos favors a different provider — see
`08-delivery-plan.md`.

If the extraction call itself fails or times out (provider outage, rate
limit, network error), the intake is set to `status = 'extraction_failed'`
rather than left stuck in a false `awaiting_confirmation` state — the
background job queue retries it a bounded number of times with backoff,
and if it still hasn't succeeded, the data officer sees a clear "extraction
failed, retry" state on their intake history with a manual **Retry**
action. This never silently drops a submitted batch.

Rather than trust the model to already know each canonical field name, the
model returns each value keyed by the label/text it actually recognized on
the page — the same kind of matching a CSV header match would have done,
just against text the model read from the image instead of a file's header
row. That returned label is then resolved against the template's aliases,
exactly like a header lookup:

```python
def match_extracted_fields(template: dict, extracted_labels: dict) -> dict:
    alias_lookup = {}
    for col in template["columns"]:
        for alias in col["aliases"]:
            alias_lookup[alias.strip().lower()] = col["canonical_field"]

    matched, unmatched = {}, []
    for label, value in extracted_labels.items():
        key = label.strip().lower()
        if key in alias_lookup:
            matched[alias_lookup[key]] = value
        else:
            unmatched.append(label)

    return {"matched": matched, "unmatched": unmatched}
```

Every value the model returns also carries its own **confidence score
(0–1)** — a separate signal from field matching. Field matching is "did we
correctly identify which canonical field this is"; confidence is "how sure
is the model that it read the value correctly." Both matter: an unmatched
label pauses the intake for manual mapping (see the template-mapping admin
screen below), while a matched-but-low-confidence value is what drives the
human field-confirmation step described next.

## Register-family cross-check

**A data officer declares which register they're submitting (ANC,
Delivery, or PNC) when they start an intake — but a wrong tap, or a
register page that got photographed out of order, shouldn't silently
publish under the wrong family.** Cureva Care checks this itself, rather than
trusting the declared `register_family` blindly: after extraction (above)
returns its labelled fields, those same labels are matched — in the
background, alongside the normal match against the declared family's
template — against the shared/default template for **all three**
families. If the fields on the page look more like a different family
than the one the officer declared, the intake is held and the officer is
asked to resolve it before anything moves on to field confirmation.

This only works because each register family has fields the others
genuinely don't capture — a **signature**, not the whole template (shared
fields like `card_number` and `referral_status` appear on all three and
carry no discriminating power, so they're excluded):

| Family | Signature fields (present on this register, not the others) |
|---|---|
| ANC | `lmp`, `edd`, `gravida`, `parity`, `gestational_age_weeks` |
| Delivery | `mode_of_delivery`, `delivery_place`, `attendant_category`, `still_birth`, `birth_weight_kg` |
| PNC | `days_postpartum`, `subject`, `maternal_assessment`, `newborn_assessment`, `feeding_status`, `danger_signs` |

```python
REGISTER_SIGNATURE_FIELDS = {
    "ANC":      {"lmp", "edd", "gravida", "parity", "gestational_age_weeks"},
    "Delivery": {"mode_of_delivery", "delivery_place", "attendant_category",
                 "still_birth", "birth_weight_kg"},
    "PNC":      {"days_postpartum", "subject", "maternal_assessment",
                 "newborn_assessment", "feeding_status", "danger_signs"},
}

def detect_register_family(extracted_labels: dict, family_templates: dict) -> dict:
    """family_templates: {'ANC': <template>, 'Delivery': <template>, 'PNC': <template>}
    — the shared/default template for each family is enough for this check,
    a facility-specific template isn't needed just to tell the families apart.
    Returns each family's count of matched signature fields."""
    scores = {}
    for family, template in family_templates.items():
        result = match_extracted_fields(template, extracted_labels)
        matched_keys = set(result["matched"].keys())
        scores[family] = len(matched_keys & REGISTER_SIGNATURE_FIELDS[family])
    return scores
```

The declared family is only overridden with the officer's explicit say-so
— the check never re-files the intake on its own:

```python
def check_register_mismatch(declared_family: str, scores: dict, min_signal: int) -> str | None:
    best_family = max(scores, key=scores.get)
    if (
        best_family != declared_family
        and scores[best_family] >= min_signal
        and scores[best_family] > scores[declared_family]
    ):
        return best_family   # suspected family, distinct enough to flag
    return None
```

`min_signal` is a `platform_settings` value
(`register_mismatch_min_signal`, see "Platform configuration and
notification preferences" in `02-data-model.md`) rather than a hard-coded
number — it exists so a false-positive rate seen during pilot can be
tuned without a code change, exactly like the AI-extraction and
identity-candidate confidence thresholds.

When `check_register_mismatch` returns a suspected family, the intake's
`register_mismatch_status` is set to `flagged` and `suspected_register_family`
is recorded, and the intake stops before field confirmation — it is
**held, not silently rejected and not silently accepted**. The data
officer sees a clear message: *"This looks like it might be a
&lt;suspected family&gt; register, not &lt;declared family&gt;. Check the
photo and choose how to proceed"* — with two ways to resolve it:

- **Confirm &lt;declared family&gt; is correct** — sets
  `register_mismatch_status = confirmed_as_declared`, records who
  confirmed it and when, and the intake proceeds exactly as if the check
  had never fired. A facility's register sometimes genuinely reuses a
  label the signature list treats as distinctive (e.g. a combined
  ANC/PNC continuation page); this is the officer's escape hatch, and it
  never blocks a legitimate submission — it only asks a human to look
  once.
- **Switch to &lt;suspected family&gt;** — sets `register_mismatch_status
  = switched`, updates the intake's `register_family` to the suspected
  family, re-resolves the template for that family
  (`resolve_template`), and re-runs extraction and field matching against
  it from the top. This is the normal case when the officer genuinely
  picked the wrong register at the start.

Either way, the resolution is recorded (`register_mismatch_resolved_by`,
`register_mismatch_resolved_at`) — this is an audit event like every
other human decision in the intake pipeline, not a silent correction.

## Live matching feedback (upload UX) — the "labor illusion" effect

**Design principle:** this is a deliberate application of what's known in
UX/behavioral-economics research as the **labor illusion** — people trust
and value a result more when they can see the system visibly working for
it, step by step, rather than staring at a blank spinner and getting a
result with no visible effort behind it. Kayak's "searching 200 airlines,"
LinkedIn's "analyzing your profile" — same principle. Cureva Care's version of
it is the live field-by-field extraction checklist, and it's a real,
named part of the intake design, not an incidental animation — anyone
touching this screen later should know it's intentional and keep it.

The moment a data officer presses **Extract** on their staged pages (see
above), the extraction step is shown happening in real time rather than
as a spinner-then-result. The screen lists the register's fields top to
bottom, in the template's order, each starting in a "reading..." state
and flipping to a checkmark the instant that field is extracted and
matched — a visible, sequential "scanning and matching" effect, not a
static wait.

Unlike a purely cosmetic labor-illusion animation, this one doesn't need
to be faked: the vision model genuinely takes real seconds per field, so
each tick reflects true extraction completion — no artificial pacing is
needed the way it would be for an instant, in-memory lookup. The effect
and the reality line up, which is what makes it trustworthy rather than
gimmicky.

A field that doesn't match anything gets a distinct "needs mapping" icon
instead of a checkmark, and does **not** block the rest of the sequence —
every other field keeps ticking down while that one sits flagged. The
sequence ends on a short summary (e.g. "9 of 10 fields matched · 1 needs
mapping," or "All 10 fields matched" when nothing is flagged) with two
actions: **Start another intake** (returns to the beginning of the flow
for the next register page), and **Confirm flagged field** — or, once
every field is clean, the equivalent action into the field-confirmation
screen — which is disabled/absent when there's nothing left to resolve.

**Unless the register-family cross-check (above) fires first.** That
check runs as part of the same extraction pass, so if the fields ticking
down look more like a different register family than the one the officer
declared, the sequence doesn't end on the normal summary — it ends on a
distinct, impossible-to-miss banner instead: *"This looks like it might
be a Delivery register, not Antenatal (ANC). Check the photo and choose
how to proceed,"* with **Confirm ANC is correct** and **Switch to
Delivery** as the two actions (see "Register-family cross-check" above
for what each does). Neither **Start another intake** nor **Confirm
flagged field** is offered until this is resolved — a suspected wrong
register is a different kind of problem from a low-confidence field, and
it gets a different, harder-to-miss stop.

Mechanically, this needs a live channel from backend to frontend, not a
single request/response — implemented as a Server-Sent Events (SSE) stream
from Django (one-directional, simpler than a full WebSocket, and a good
fit for "stream of progress updates"). See `04-architecture-and-stack.md`
and `05-api-routes.md`.

## Facility flagging vs. admin approval

A data officer can **flag** that their submission doesn't look right —
a lightweight "this doesn't match what I expected" report attached to the
intake, with an optional note. Flagging never creates or changes a
template by itself. Only a Systems admin can turn a flag (or an
unmatched-field pause) into an actual new or updated template. This is a
deliberate governance boundary: easy to report a problem, controlled who
can make something official.

```sql
CREATE TABLE template_flags (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_id    UUID NOT NULL REFERENCES intakes(id),
    flagged_by   UUID NOT NULL REFERENCES users(id),
    note         TEXT NULL,
    status       TEXT NOT NULL DEFAULT 'open', -- open | resolved
    resolved_by  UUID NULL REFERENCES users(id),
    resolved_template_id UUID NULL REFERENCES templates(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## Template-mapping admin screen

A page in the Next.js app (calling the Django API), restricted to the
Systems admin role, that covers the full template lifecycle:

- Shows unmatched extracted labels and any open facility flags for a given
  intake, alongside a searchable list of canonical fields.
- Lets the admin manually map a label to a canonical field for this one
  intake, and choose how to persist that mapping:
  - **"Save as alias on the current template"** — if this facility already
    has its own template, or if the change should apply to every facility
    using the shared default.
  - **"Create a facility-specific template"** — clones the currently
    resolved template (facility-specific or shared) into a new version
    scoped to this facility, then applies the mapping there. This is how a
    facility with a genuinely different form gets permanently decoupled
    from the shared default without affecting anyone else.
- Only an admin action here can resolve an open `template_flags` row.
- Lists all templates (shared and per-facility), their versions, and which
  facilities are using which version.
- Every change writes a **new template version** — never edits a version in
  place (rule #2: nothing is silently overwritten). Old intakes keep
  pointing at the template version they were actually validated against.

## Mandatory human confirmation before publish

Every row lands as `status = 'awaiting_confirmation'`, unconditionally —
there is no "declared reviewed, publish directly" shortcut, because there
is no channel trusted enough to skip this. The whole point of confidence
scoring is that a human has to look, so the system never gives itself
permission to skip that.

The confirmation screen shows each extracted row next to the cropped
region of the original image it came from, per field
(`field_image_regions` drives this), with low-confidence fields (below a
configurable threshold — start around 0.85) visibly highlighted. The
reviewer confirms each flagged field as correct, or types the correction.
High-confidence fields are shown but not forced into an individual click —
the reviewer can confirm a whole row at once when nothing is flagged, and
drill into only the flagged fields otherwise, so this doesn't become a
click-every-cell chore.

Once every field below the confidence threshold has been confirmed or
corrected, `confirmed_by`/`confirmed_at` are set and the row can publish
(identity resolution, maternal projection, intelligence). A correction
made here is recorded the same way any other correction is (see
`02-data-model.md`'s correction history) — the AI's original guess is
never silently lost, it's kept alongside the human's corrected value.

What this deliberately does **not** do: the model never confirms its own
extraction, never raises a row's status past `awaiting_confirmation` on
its own, and never gets treated as a second independent reviewer for
anything the identity-linkage or template-approval flows already require a
human for. It populates; a person verifies. That boundary is what keeps
rule #3 (unverified data doesn't count) and the identity-linkage
confirmation rule intact.

Expect extraction accuracy to vary — handwriting varies by officer and
register condition varies by facility. Track per-field
confirmation-vs-correction rates from the first pilot images and use them
to tune the confidence threshold; don't hand-pick a threshold once and
leave it.

## Intake validation, in order

1. **Fingerprint check** — compute source_hash on the image file(s); if it
   matches an existing intake for this (facility,
   register_family), reject as a duplicate no-op.
2. **Template resolution** — run `resolve_template` for this facility and
   register family (facility-specific template first, shared default as
   fallback). Record the resolved `template_id` on the intake permanently.
3. **Extraction and field matching** — run the vision model against the
   resolved template, then `match_extracted_fields` against its labelled
   output. Unmatched labels pause the intake for manual mapping (see the
   admin screen above — this is also the point where a facility-specific
   template gets created if needed).
4. **Register-family cross-check** — using the same extracted labels,
   run `detect_register_family` against all three families' signatures
   (see "Register-family cross-check" above). If the fields look more
   like a different family than the one declared, the intake is held —
   not published, not even passed to field confirmation — until the data
   officer confirms the declared family or switches to the suspected one.
5. **Type/structure validation** — each matched field checked against its
   declared type (date, integer, decimal, enum).
6. **Plausibility checks** — values outside `plausible_range` (where
   defined) are flagged as warnings on the row, not blocked — they still
   publish once verified, but are visibly flagged for follow-up in the
   Records view.
7. **Field confirmation** — every field below the confidence threshold
   must be confirmed or corrected by a human reviewer before the row can
   proceed.
8. **Identity resolution** — for each row, attempt the strict-identifier
   fast path, then probabilistic candidate matching if that fails (see
   `02-data-model.md`).
9. **Publish or hold** — per the publication mode (see
   `01-product-scope.md`). A row can only reach "publish" after step 4 is
   resolved and step 7 is complete.
