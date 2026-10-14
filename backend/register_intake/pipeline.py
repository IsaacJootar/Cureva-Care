"""Intake processing pipeline.

Orchestrates the steps in cureva-docs/03-templates-and-intake.md "Intake
validation, in order": template resolution -> extraction -> field matching ->
register-family cross-check -> type/plausibility validation -> per-field
confidence gate -> (identity resolution, Module 3) -> publish/hold.

Everything tunable (confidence threshold, cross-check min-signal) is read from
platform_settings through the shared accessor — never a literal here.
"""
from django.db import transaction
from django.utils import timezone

from identity_access.services import get_setting
from identity_access.settings_registry import (
    AI_EXTRACTION_CONFIDENCE_THRESHOLD,
    REGISTER_MISMATCH_MIN_SIGNAL,
)

from .extraction import ExtractionError, VisionExtractor, default_extractor
from .matching import check_register_mismatch, detect_register_family, match_extracted_fields
from .models import (
    Intake,
    IntakeStatus,
    RegisterMismatchStatus,
    SourceRow,
    SourceRowStatus,
)
from .resolution import resolve_template, shared_templates_by_family
from .validation import service_date_from_normalized, validate_and_normalize


def _alias_to_canonical(template: dict) -> dict:
    lookup = {}
    for col in template["columns"]:
        lookup[col["label"].strip().lower()] = col["canonical_field"]
        for alias in col["aliases"]:
            lookup[alias.strip().lower()] = col["canonical_field"]
    return lookup


def _below_threshold_fields(confidence: dict, flags: dict, threshold: float) -> list[str]:
    """Canonical fields that must be human-confirmed before publish: those read
    with low confidence, plus any with a type error."""
    need = {f for f, score in confidence.items() if score is not None and score < threshold}
    need |= {f for f, info in (flags or {}).items() if info.get("kind") == "type_error"}
    return sorted(need)


def always_confirm_fields(template_schema: dict) -> set[str]:
    """Identity-defining fields that a human must always confirm, regardless of
    AI confidence (IDENTITY_MATCHING_UPDATE.md Section A). Per-facility templates
    cannot turn this off — it's read from the template's field definitions."""
    return {
        c["canonical_field"]
        for c in (template_schema or {}).get("columns", [])
        if c.get("always_confirm")
    }


@transaction.atomic
def process_intake(intake: Intake, images: list[bytes], extractor: VisionExtractor | None = None) -> dict:
    """Run extraction + validation and (re)build this intake's source rows.

    On an extraction failure the intake moves to `extraction_failed` (retryable)
    and no rows are created. On a suspected wrong register family the intake is
    held (register_mismatch_status=flagged) — rows are still built from the
    declared template (raw preserved), but confirmation and publish are blocked
    until a human resolves it.
    """
    extractor = extractor or default_extractor()
    template = resolve_template(intake.register_family, intake.facility_id)
    intake.template = template
    intake.extraction_engine = extractor.engine_name

    try:
        extracted_rows = extractor.extract(images, template.schema)
    except ExtractionError:
        intake.status = IntakeStatus.EXTRACTION_FAILED
        intake.save(update_fields=["status", "template", "extraction_engine"])
        return {"status": "extraction_failed"}

    threshold = float(get_setting(AI_EXTRACTION_CONFIDENCE_THRESHOLD))
    alias_lookup = _alias_to_canonical(template.schema)

    # Rebuild rows idempotently (safe to re-run, e.g. after a switch).
    intake.rows.all().delete()

    # Aggregate all labels across rows for the register-family cross-check.
    all_labels: dict = {}
    for row in extracted_rows:
        all_labels.update(row.get("fields", {}))

    scores = detect_register_family(all_labels, shared_templates_by_family())
    min_signal = int(get_setting(REGISTER_MISMATCH_MIN_SIGNAL))
    suspected = check_register_mismatch(intake.register_family, scores, min_signal)

    unmatched_all: set[str] = set()
    for i, row in enumerate(extracted_rows, start=1):
        labels = row.get("fields", {})
        conf_by_label = row.get("confidence", {})
        matched = match_extracted_fields(template.schema, labels)
        unmatched_all.update(matched["unmatched"])

        result = validate_and_normalize(template.schema, matched["matched"])
        normalized, flags = result["normalized"], result["flags"]

        # Remap confidence from the labels read to canonical fields.
        confidence: dict = {}
        for label, score in conf_by_label.items():
            canon = alias_lookup.get(label.strip().lower())
            if canon:
                confidence[canon] = score

        SourceRow.objects.create(
            intake=intake,
            row_number=i,
            raw_payload=labels,
            normalized=normalized,
            service_date=service_date_from_normalized(intake.register_family, normalized),
            status=SourceRowStatus.AWAITING_CONFIRMATION,
            flags=flags or None,
            extraction_confidence=confidence,
            confirmed_fields=[],
            unmatched_labels=matched["unmatched"],
        )
        _ = _below_threshold_fields(confidence, flags, threshold)  # computed at read time too

    if suspected:
        intake.suspected_register_family = suspected
        intake.register_mismatch_status = RegisterMismatchStatus.FLAGGED
    else:
        intake.suspected_register_family = None
        if intake.register_mismatch_status == RegisterMismatchStatus.FLAGGED:
            # a previous flag that no longer applies after a re-run
            intake.register_mismatch_status = RegisterMismatchStatus.NOT_APPLICABLE

    intake.status = IntakeStatus.AWAITING_CONFIRMATION
    intake.save(
        update_fields=[
            "template",
            "extraction_engine",
            "status",
            "suspected_register_family",
            "register_mismatch_status",
        ]
    )

    return {
        "status": "held_mismatch" if suspected else "rows_created",
        "suspected_register_family": suspected,
        "row_count": len(extracted_rows),
        "unmatched_labels": sorted(unmatched_all),
    }


def row_needs_confirmation(row: SourceRow, threshold: float, template_schema: dict | None = None) -> list[str]:
    """Fields on this row still needing human confirmation: those read with low
    confidence or a type error, PLUS every always-confirm identity field that
    carries a value (regardless of confidence). A row can't publish until all of
    these are confirmed or corrected (IDENTITY_MATCHING_UPDATE.md Sections A)."""
    if template_schema is None and getattr(row, "intake", None) and row.intake.template_id:
        template_schema = row.intake.template.schema

    pending = set(_below_threshold_fields(row.extraction_confidence, row.flags, threshold))
    if template_schema:
        normalized = row.normalized or {}
        for field in always_confirm_fields(template_schema):
            if normalized.get(field) not in (None, ""):
                pending.add(field)
    return sorted(f for f in pending if f not in (row.confirmed_fields or []))


def resolve_register_mismatch(intake: Intake, action: str, user, images: list[bytes], extractor=None) -> dict:
    """Resolve a flagged register-family mismatch (cureva-docs/03).

    action = 'confirm_declared' -> keep the declared family, clear the hold.
    action = 'switch'           -> adopt the suspected family, re-resolve the
                                   template, and re-run extraction from the top.
    """
    if intake.register_mismatch_status != RegisterMismatchStatus.FLAGGED:
        raise ValueError("No flagged register-family mismatch to resolve.")

    if action == "confirm_declared":
        intake.register_mismatch_status = RegisterMismatchStatus.CONFIRMED_AS_DECLARED
        intake.register_mismatch_resolved_by = user
        intake.register_mismatch_resolved_at = timezone.now()
        intake.suspected_register_family = None
        intake.save(
            update_fields=[
                "register_mismatch_status",
                "register_mismatch_resolved_by",
                "register_mismatch_resolved_at",
                "suspected_register_family",
            ]
        )
        return {"status": "confirmed_as_declared"}

    if action == "switch":
        new_family = intake.suspected_register_family
        intake.register_family = new_family
        intake.register_mismatch_status = RegisterMismatchStatus.SWITCHED
        intake.register_mismatch_resolved_by = user
        intake.register_mismatch_resolved_at = timezone.now()
        intake.save(
            update_fields=[
                "register_family",
                "register_mismatch_status",
                "register_mismatch_resolved_by",
                "register_mismatch_resolved_at",
            ]
        )
        # Re-run against the correct family. process_intake may re-flag if the
        # page still looks like yet another family, but the switched status and
        # audit fields are preserved below.
        result = process_intake(intake, images, extractor)
        if result["status"] != "held_mismatch":
            intake.register_mismatch_status = RegisterMismatchStatus.SWITCHED
            intake.save(update_fields=["register_mismatch_status"])
        return {"status": "switched", "reprocess": result}

    raise ValueError(f"Unknown resolution action: {action!r}")
