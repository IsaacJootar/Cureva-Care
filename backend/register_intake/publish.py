"""Field confirmation and the publish/hold gate.

A row only reaches `published` after: the register-family mismatch (if any) is
resolved, and every below-confidence-threshold / type-error field has been
confirmed or corrected by a human. Implausible values are flagged but do not
block — they publish once the row is verified, visibly flagged (cureva-docs/03,
06). Publish is idempotent (rule: safe to call twice).
"""
from django.db import transaction
from django.utils import timezone

from identity_access.services import get_setting
from identity_access.settings_registry import AI_EXTRACTION_CONFIDENCE_THRESHOLD

from .models import (
    FieldCorrection,
    Intake,
    IntakeStatus,
    RegisterMismatchStatus,
    SourceRow,
    SourceRowStatus,
)
from .pipeline import row_needs_confirmation


class PublishError(Exception):
    pass


@transaction.atomic
def confirm_field(row: SourceRow, field: str, corrected_value, user, correct: bool) -> SourceRow:
    """Confirm (value was right) or correct (value changed) one field.

    Either way the field is marked handled. A correction is recorded in the
    append-only correction history — the model's original guess is never lost
    (rule #1). `correct=True` means a correction is being applied.
    """
    normalized = dict(row.normalized or {})
    previous = normalized.get(field)

    if correct:
        FieldCorrection.objects.create(
            source_row=row,
            field=field,
            previous_value=previous,
            corrected_value=corrected_value,
            corrected_by=user,
        )
        normalized[field] = corrected_value
        row.normalized = normalized
        # A correction clears a type-error flag on that field.
        if row.flags and field in row.flags and row.flags[field].get("kind") == "type_error":
            flags = dict(row.flags)
            del flags[field]
            row.flags = flags or None

    handled = list(row.confirmed_fields or [])
    if field not in handled:
        handled.append(field)
    row.confirmed_fields = handled
    row.save(update_fields=["normalized", "flags", "confirmed_fields"])
    return row


def intake_publishable(intake: Intake) -> tuple[bool, str]:
    """(ok, reason). Checks the register-family hold and every row's gate."""
    if intake.register_mismatch_status == RegisterMismatchStatus.FLAGGED:
        return False, "Register-family mismatch must be resolved first."
    threshold = float(get_setting(AI_EXTRACTION_CONFIDENCE_THRESHOLD))
    for row in intake.rows.all():
        pending = row_needs_confirmation(row, threshold)
        if pending:
            return False, f"Row {row.row_number} has unconfirmed fields: {', '.join(pending)}."
    return True, ""


@transaction.atomic
def publish_intake(intake: Intake, user) -> dict:
    """Idempotently publish an intake once every gate is satisfied. Relies on
    the intake's status + a DB transaction, not client-side de-duplication."""
    # Lock the row to make concurrent publishes safe.
    intake = Intake.objects.select_for_update().get(pk=intake.pk)

    if intake.status == IntakeStatus.PUBLISHED:
        return {"status": "published", "already": True}

    ok, reason = intake_publishable(intake)
    if not ok:
        raise PublishError(reason)

    now = timezone.now()
    for row in intake.rows.all():
        row.status = SourceRowStatus.VERIFIED
        row.confirmed_by = user
        row.confirmed_at = now
        row.save(update_fields=["status", "confirmed_by", "confirmed_at"])

    intake.status = IntakeStatus.PUBLISHED
    intake.published_at = now
    intake.save(update_fields=["status", "published_at"])

    # Identity resolution runs now (strict fast path, then probabilistic
    # candidate queuing). Maternal event projection follows in Module 4.
    # Imported lazily to keep the app boundary clean.
    from maternal_projection.identity import resolve_identity

    identity_results = []
    for row in intake.rows.all():
        identity_results.append(resolve_identity(row))

    return {"status": "published", "already": False, "rows": intake.rows.count(), "identity": identity_results}
