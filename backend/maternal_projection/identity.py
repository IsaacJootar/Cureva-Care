"""Identity resolution: strict fast path + probabilistic candidate matching.

Updated per IDENTITY_MATCHING_UPDATE.md:
- Section B: a card-number match auto-links ONLY if the name is similar enough
  and the match is recent; otherwise it goes to the review queue with a reason.
- Section C: a woman is recognised by ANY identifier she has used
  (woman_identifiers), not just one; confirming a candidate adds the new row's
  identifiers so the next pregnancy/register is easier.
- Section E: a Delivery/PNC row's ANC number is looked up as the strongest
  cross-register signal.

Nothing is ever auto-merged on demographics alone; only a human confirmation
links a probabilistic candidate (cureva-docs/02).
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from identity_access.models import AuditEvent
from identity_access.services import get_setting
from identity_access.settings_registry import (
    IDENTITY_CANDIDATE_CONFIDENCE_THRESHOLD,
    IDENTITY_CARD_REUSE_WINDOW_DAYS,
    IDENTITY_STRICT_NAME_FLOOR,
)

from .models import (
    CandidateStatus,
    IdentityCandidate,
    LinkMethod,
    SourceRowLink,
    Woman,
    WomanIdentifier,
)
from .name_matching import name_similarity


def _norm_card(v):
    return str(v).strip().upper() if v not in (None, "") else None


def _norm_phone(v):
    if v in (None, ""):
        return None
    digits = "".join(ch for ch in str(v) if ch.isdigit())
    return digits or None


def _demographics(normalized: dict) -> dict:
    name = normalized.get("name") or normalized.get("woman_name")
    phone = normalized.get("phone") or normalized.get("cl_phone")
    return {
        "name": name,
        "phone": _norm_phone(phone),
        "date_of_birth": normalized.get("date_of_birth") or normalized.get("dob"),
        "age": normalized.get("age"),
        "card_number": _norm_card(normalized.get("card_number")),
        "anc_number": _norm_card(normalized.get("anc_number")),
    }


def _row_service_date(source_row):
    return source_row.service_date or source_row.intake.batch_period_from


def _add_identifier(woman, facility_id, kind, value, register_family, source_row, service_date, added_via):
    if not value:
        return
    existing = WomanIdentifier.objects.filter(woman=woman, kind=kind, value=value).first()
    if existing:
        if service_date and (existing.last_seen_at is None or service_date > existing.last_seen_at):
            existing.last_seen_at = service_date
            existing.save(update_fields=["last_seen_at"])
        return
    WomanIdentifier.objects.create(
        woman=woman, facility_id=facility_id, kind=kind, value=value,
        register_family=register_family, first_source_row=source_row,
        last_seen_at=service_date, added_via=added_via,
    )


def _store_row_identifiers(woman, source_row, demo, family, added_via):
    """Record this row's card/ANC numbers, phone, and name spelling on the woman."""
    svc = _row_service_date(source_row)
    fid = source_row.intake.facility_id
    _add_identifier(woman, fid, "card_number", demo["card_number"], family.lower(), source_row, svc, added_via)
    _add_identifier(woman, fid, "card_number", demo["anc_number"], "anc", source_row, svc, added_via)
    _add_identifier(woman, fid, "phone", demo["phone"], None, source_row, svc, added_via)
    if demo["name"]:
        from .name_matching import normalized_name
        _add_identifier(woman, fid, "name_variant", normalized_name(demo["name"]), None, source_row, svc, added_via)


def _find_by_card(facility_id, values):
    """Find a woman by any card-number value at this facility. Returns
    (woman, last_seen_at) or None. Checks the identifier history first, then
    falls back to the woman's primary stable_identifier (self-heals: a strict
    link then records the identifier). ANC-number lookups are the strongest
    signal, so pass those first."""
    for value in values:
        if not value:
            continue
        ident = (
            WomanIdentifier.objects.filter(facility_id=facility_id, kind="card_number", value=value)
            .select_related("woman")
            .order_by("-last_seen_at")
            .first()
        )
        if ident:
            return ident.woman, ident.last_seen_at
        woman = Woman.objects.filter(facility_id=facility_id, stable_identifier=value).first()
        if woman:
            return woman, None
    return None


def _name_check(row_name, woman_name, floor) -> tuple[bool, str | None]:
    """(ok, reason). When neither side has a name there's nothing to verify, so
    the check passes and we rely on card + recency."""
    if not row_name and not woman_name:
        return True, None
    if not row_name:
        return False, "card_match_name_missing"
    if not woman_name:
        return True, None  # row has a name, woman didn't — accept and store it
    if name_similarity(row_name, woman_name) >= floor:
        return True, None
    return False, "card_match_name_conflict"


def _queue_candidate(source_row, woman, facility_id, confidence, matched_fields, reason):
    IdentityCandidate.objects.create(
        source_row=source_row, candidate_woman=woman, facility_id=facility_id,
        confidence=round(confidence, 3), matched_fields=matched_fields,
        reason=reason, status=CandidateStatus.PENDING,
    )


def score_candidate(row_demo: dict, woman: Woman) -> tuple[float, dict]:
    """Weighted similarity in [0,1] with a breakdown, comparing against the
    woman's recorded name and any of her phone identifiers."""
    matched = {}
    score = 0.0

    best_name = name_similarity(row_demo.get("name") or "", woman.name or "")
    for ident in woman.identifiers.filter(kind="name_variant"):
        best_name = max(best_name, name_similarity(row_demo.get("name") or "", ident.value))
    if best_name > 0:
        matched["name"] = round(best_name, 3)
        score += 0.55 * best_name

    row_phone = row_demo.get("phone")
    woman_phones = {woman.phone and _norm_phone(woman.phone)} | {
        i.value for i in woman.identifiers.filter(kind="phone")
    }
    if row_phone and row_phone in {p for p in woman_phones if p}:
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
def resolve_identity(source_row, actor=None) -> dict:
    """Resolve one verified source row's identity. Idempotent."""
    if SourceRowLink.objects.filter(source_row=source_row).exists():
        return {"linked": True, "method": "already_linked"}

    normalized = source_row.normalized or {}
    facility_id = source_row.intake.facility_id
    family = source_row.intake.register_family
    demo = _demographics(normalized)
    svc = _row_service_date(source_row)

    name_floor = float(get_setting(IDENTITY_STRICT_NAME_FLOOR))
    reuse_window = int(get_setting(IDENTITY_CARD_REUSE_WINDOW_DAYS))

    # --- Strict fast path (card / ANC number), with the two extra checks ---
    # ANC number is the strongest cross-register signal, so look it up first.
    match = _find_by_card(facility_id, [demo["anc_number"], demo["card_number"]])

    if match is not None:
        woman, last_seen_at = match
        name_ok, name_reason = _name_check(demo["name"], woman.name, name_floor)

        recency_ok = True
        if last_seen_at and svc:
            if (svc - last_seen_at) > timedelta(days=reuse_window):
                recency_ok = False

        if name_ok and recency_ok:
            SourceRowLink.objects.create(source_row=source_row, woman=woman, method=LinkMethod.STRICT, linked_by=None)
            _store_row_identifiers(woman, source_row, demo, family, "strict")
            return {"linked": True, "method": "strict", "woman_id": str(woman.id), "created_woman": False}

        reason = name_reason if not name_ok else "card_match_stale"
        _queue_candidate(source_row, woman, facility_id, 0.90,
                         {"card_number": True, "name": name_similarity(demo["name"] or "", woman.name or "")}, reason)
        return {"linked": False, "method": "review", "reason": reason}

    # --- Card unknown (or absent): try to recognise her by demographics first,
    # so a NEW card number for a known woman (e.g. a second pregnancy) becomes a
    # review candidate rather than a silent new/duplicate woman. ---
    if IdentityCandidate.objects.filter(source_row=source_row).exists():
        return {"linked": False, "method": "candidates_exist"}

    threshold = float(get_setting(IDENTITY_CANDIDATE_CONFIDENCE_THRESHOLD))
    candidates = []
    if demo.get("name") or demo.get("phone"):
        for woman in Woman.objects.filter(facility_id=facility_id):
            conf, matched = score_candidate(demo, woman)
            if conf >= threshold:
                candidates.append((woman, conf, matched))
    if candidates:
        for woman, conf, matched in candidates:
            _queue_candidate(source_row, woman, facility_id, conf, matched, "probabilistic")
        return {"linked": False, "method": "candidates_created", "candidates": len(candidates)}

    # Genuine first sighting of this card → create the woman (strict).
    if demo["card_number"] or demo["anc_number"]:
        woman = Woman.objects.create(
            facility_id=facility_id,
            stable_identifier=demo["card_number"] or demo["anc_number"],
            name=demo.get("name"), phone=demo.get("phone"), age=demo.get("age"),
        )
        SourceRowLink.objects.create(source_row=source_row, woman=woman, method=LinkMethod.STRICT, linked_by=None)
        _store_row_identifiers(woman, source_row, demo, family, "strict")
        return {"linked": True, "method": "strict", "woman_id": str(woman.id), "created_woman": True}

    # No identifier and no demographic match → unlinked encounter (still counted).
    return {"linked": False, "method": "unlinked_encounter"}


@transaction.atomic
def confirm_candidate(candidate: IdentityCandidate, user) -> dict:
    """Human confirmation — the ONLY path that links a candidate. Adds the row's
    identifiers to the woman so the next sighting resolves more easily."""
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
        defaults={"woman": candidate.candidate_woman, "method": LinkMethod.CANDIDATE_CONFIRMED, "linked_by": user},
    )

    demo = _demographics(candidate.source_row.normalized or {})
    family = candidate.source_row.intake.register_family
    _store_row_identifiers(candidate.candidate_woman, candidate.source_row, demo, family, "confirmed_candidate")

    IdentityCandidate.objects.filter(
        source_row=candidate.source_row, status=CandidateStatus.PENDING
    ).exclude(pk=candidate.pk).update(
        status=CandidateStatus.REJECTED, reviewed_by=user, reviewed_at=timezone.now()
    )

    AuditEvent.objects.create(
        actor=user, event_type="identity_candidate_confirmed",
        subject_type="identity_candidate", subject_id=candidate.id, facility_id=candidate.facility_id,
        metadata={"confidence": str(candidate.confidence), "reason": candidate.reason},
    )

    from .projection import project_row
    project_row(candidate.source_row)
    from intelligence.aggregation import rebuild_facility_metrics
    rebuild_facility_metrics(candidate.facility_id)

    return {"status": "confirmed", "woman_id": str(candidate.candidate_woman_id)}


@transaction.atomic
def reject_candidate(candidate: IdentityCandidate, user) -> dict:
    if candidate.status != CandidateStatus.PENDING:
        return {"status": candidate.status}
    candidate.status = CandidateStatus.REJECTED
    candidate.reviewed_by = user
    candidate.reviewed_at = timezone.now()
    candidate.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    AuditEvent.objects.create(
        actor=user, event_type="identity_candidate_rejected",
        subject_type="identity_candidate", subject_id=candidate.id, facility_id=candidate.facility_id,
        metadata={"confidence": str(candidate.confidence)},
    )
    return {"status": "rejected"}


# Backwards-compatible helper retained for any external callers.
def _old_score(row_demo, woman):  # pragma: no cover
    return score_candidate(row_demo, woman)
