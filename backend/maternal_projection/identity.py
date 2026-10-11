"""Identity resolution: strict fast path + probabilistic candidate matching.

Two paths, both built (cureva-docs/02-data-model.md):
1. Strict: a row with a stable identifier (card/folder number) links
   automatically — to an existing Woman with that identifier, or by creating a
   new Woman. No human review.
2. Probabilistic: with no identifier, compare demographics (name, DOB/age,
   phone) to existing Women at the facility, score the match, and — at/above
   the configurable threshold — queue an IdentityCandidate for human review.
   Below threshold the row stays an unlinked encounter (still counted in
   facility totals, just not in per-woman continuity). NOTHING is ever
   auto-merged on demographic similarity; only a human confirmation links it.
"""
from difflib import SequenceMatcher

from django.db import transaction
from django.utils import timezone

from identity_access.models import AuditEvent
from identity_access.services import get_setting
from identity_access.settings_registry import IDENTITY_CANDIDATE_CONFIDENCE_THRESHOLD

from .models import (
    CandidateStatus,
    IdentityCandidate,
    LinkMethod,
    SourceRowLink,
    Woman,
)


def _norm_name(s):
    return " ".join((s or "").strip().lower().split())


def _name_similarity(a, b):
    a, b = _norm_name(a), _norm_name(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _demographics(normalized: dict) -> dict:
    return {
        "name": normalized.get("name") or normalized.get("woman_name"),
        "phone": (normalized.get("phone") or normalized.get("cl_phone") or "").strip() or None
        if isinstance(normalized.get("phone") or normalized.get("cl_phone"), str)
        else normalized.get("phone"),
        "date_of_birth": normalized.get("date_of_birth") or normalized.get("dob"),
        "age": normalized.get("age"),
    }


def score_candidate(row_demo: dict, woman: Woman) -> tuple[float, dict]:
    """Weighted similarity in [0,1] with a breakdown of what contributed."""
    matched = {}
    score = 0.0

    name_sim = _name_similarity(row_demo.get("name"), woman.name)
    if name_sim > 0:
        matched["name"] = round(name_sim, 3)
        score += 0.55 * name_sim

    row_phone = row_demo.get("phone")
    if row_phone and woman.phone and str(row_phone).strip() == str(woman.phone).strip():
        matched["phone"] = True
        score += 0.30

    row_dob = row_demo.get("date_of_birth")
    if row_dob and woman.date_of_birth and str(row_dob) == str(woman.date_of_birth):
        matched["date_of_birth"] = True
        score += 0.15
    elif row_demo.get("age") and woman.age and abs(int(row_demo["age"]) - int(woman.age)) <= 1:
        matched["age"] = True
        score += 0.07

    return min(score, 1.0), matched


@transaction.atomic
def resolve_identity(source_row, actor=None, threshold: float | None = None) -> dict:
    """Resolve one verified source row's identity. Idempotent: a row that is
    already linked, or that already has pending candidates, is not reprocessed."""
    if SourceRowLink.objects.filter(source_row=source_row).exists():
        return {"linked": True, "method": "already_linked"}

    normalized = source_row.normalized or {}
    facility_id = source_row.intake.facility_id
    stable_id = normalized.get("card_number")
    stable_id = str(stable_id).strip() if stable_id else None

    # --- Strict fast path ---
    if stable_id:
        woman = Woman.objects.filter(facility_id=facility_id, stable_identifier=stable_id).first()
        created = False
        if woman is None:
            demo = _demographics(normalized)
            woman = Woman.objects.create(
                facility_id=facility_id,
                stable_identifier=stable_id,
                name=demo.get("name"),
                phone=demo.get("phone"),
                age=demo.get("age"),
            )
            created = True
        SourceRowLink.objects.create(
            source_row=source_row, woman=woman, method=LinkMethod.STRICT, linked_by=None
        )
        return {"linked": True, "method": "strict", "woman_id": str(woman.id), "created_woman": created}

    # --- Probabilistic candidate matching ---
    if IdentityCandidate.objects.filter(source_row=source_row).exists():
        return {"linked": False, "method": "candidates_exist"}

    row_demo = _demographics(normalized)
    if not row_demo.get("name") and not row_demo.get("phone"):
        return {"linked": False, "method": "unlinked_encounter", "reason": "no_identifier_no_demographics"}

    threshold = threshold if threshold is not None else float(get_setting(IDENTITY_CANDIDATE_CONFIDENCE_THRESHOLD))
    created = 0
    for woman in Woman.objects.filter(facility_id=facility_id):
        conf, matched = score_candidate(row_demo, woman)
        if conf >= threshold:
            IdentityCandidate.objects.create(
                source_row=source_row,
                candidate_woman=woman,
                facility_id=facility_id,
                confidence=round(conf, 3),
                matched_fields=matched,
                status=CandidateStatus.PENDING,
            )
            created += 1
    return {"linked": False, "method": "candidates_created", "candidates": created}


@transaction.atomic
def confirm_candidate(candidate: IdentityCandidate, user) -> dict:
    """Human confirmation — the ONLY path that links a candidate. Requires a
    reviewing user; merges the row into the candidate Woman and audits it."""
    if user is None:
        raise ValueError("A reviewing user is required to confirm a candidate.")
    if candidate.status != CandidateStatus.PENDING:
        return {"status": candidate.status}

    candidate.status = CandidateStatus.CONFIRMED
    candidate.reviewed_by = user
    candidate.reviewed_at = timezone.now()
    candidate.save(update_fields=["status", "reviewed_by", "reviewed_at"])

    SourceRowLink.objects.get_or_create(
        source_row=candidate.source_row,
        defaults={
            "woman": candidate.candidate_woman,
            "method": LinkMethod.CANDIDATE_CONFIRMED,
            "linked_by": user,
        },
    )
    # The row is now linked — other pending candidates for it no longer apply.
    IdentityCandidate.objects.filter(
        source_row=candidate.source_row, status=CandidateStatus.PENDING
    ).exclude(pk=candidate.pk).update(
        status=CandidateStatus.REJECTED, reviewed_by=user, reviewed_at=timezone.now()
    )

    AuditEvent.objects.create(
        actor=user, event_type="identity_candidate_confirmed",
        subject_type="identity_candidate", subject_id=candidate.id,
        facility_id=candidate.facility_id,
        metadata={"confidence": str(candidate.confidence), "matched_fields": candidate.matched_fields},
    )
    return {"status": "confirmed", "woman_id": str(candidate.candidate_woman_id)}


@transaction.atomic
def reject_candidate(candidate: IdentityCandidate, user) -> dict:
    """Human rejection — the row stays an unlinked encounter. Audited."""
    if candidate.status != CandidateStatus.PENDING:
        return {"status": candidate.status}
    candidate.status = CandidateStatus.REJECTED
    candidate.reviewed_by = user
    candidate.reviewed_at = timezone.now()
    candidate.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    AuditEvent.objects.create(
        actor=user, event_type="identity_candidate_rejected",
        subject_type="identity_candidate", subject_id=candidate.id,
        facility_id=candidate.facility_id,
        metadata={"confidence": str(candidate.confidence)},
    )
    return {"status": "rejected"}
