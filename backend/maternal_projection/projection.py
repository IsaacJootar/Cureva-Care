"""Project verified, identity-linked source rows into the maternal model.

Only linked rows project (a row contributes to per-woman continuity once it has
a SourceRowLink — strict or confirmed candidate; cureva-docs/02). Unlinked
encounters stay as source rows and still count in facility operational totals.
Idempotent: a row already projected is not projected again.
"""
from datetime import date

from django.db import transaction

from .models import (
    ANCContact,
    BirthEvent,
    EpisodeStatus,
    PNCContact,
    PregnancyEpisode,
    Referral,
    SourceRowLink,
)


def _d(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _already_projected(source_row) -> bool:
    return (
        ANCContact.objects.filter(source_row=source_row).exists()
        or BirthEvent.objects.filter(source_row=source_row).exists()
        or PNCContact.objects.filter(source_row=source_row).exists()
    )


def _create_episode(woman, facility_id, norm):
    n = PregnancyEpisode.objects.filter(woman=woman).count() + 1
    return PregnancyEpisode.objects.create(
        woman=woman,
        facility_id=facility_id,
        episode_number=n,
        lmp=_d(norm.get("lmp")),
        edd=_d(norm.get("edd")),
        booking_date=_d(norm.get("booking_date")),
        booking_gestational_age_weeks=norm.get("gestational_age_weeks"),
        status=EpisodeStatus.ACTIVE,
    )


def _episode_has_outcome(episode):
    return episode.status in (EpisodeStatus.DELIVERED, EpisodeStatus.CLOSED) or BirthEvent.objects.filter(
        episode=episode
    ).exists()


def _episode_outcome_date(episode):
    return BirthEvent.objects.filter(episode=episode).values_list("delivery_date", flat=True).first()


def _resolve_episode(woman, facility_id, norm, family, service_date):
    """Attach the row to the right pregnancy episode, opening a new one per the
    rules in IDENTITY_MATCHING_UPDATE.md Section D (ANC) / Section E (Delivery,
    PNC)."""
    from identity_access.services import get_setting
    from identity_access.settings_registry import NEW_EPISODE_GAP_DAYS

    latest = PregnancyEpisode.objects.filter(woman=woman).order_by("-created_at").first()
    if latest is None:
        return _create_episode(woman, facility_id, norm)

    if family == "PNC":
        # Most recent episode with a delivery on or before this visit.
        for ep in PregnancyEpisode.objects.filter(woman=woman).order_by("-created_at"):
            od = _episode_outcome_date(ep)
            if od and service_date and od <= service_date:
                return ep
        return latest

    if family == "Delivery":
        # Prefer an open (not-yet-delivered) episode.
        open_ep = (
            PregnancyEpisode.objects.filter(woman=woman)
            .exclude(status=EpisodeStatus.DELIVERED)
            .order_by("-created_at")
            .first()
        )
        return open_ep or latest

    # --- ANC (Section D) ---
    gap = int(get_setting(NEW_EPISODE_GAP_DAYS))
    # (a) latest episode already has an outcome dated before this row → new episode
    if _episode_has_outcome(latest):
        od = _episode_outcome_date(latest)
        if service_date and od and od < service_date:
            return _create_episode(woman, facility_id, norm)
    # (b) too long after the latest booking with no outcome → new episode
    elif latest.booking_date and service_date and (service_date - latest.booking_date).days > gap:
        return _create_episode(woman, facility_id, norm)

    return latest


def _as_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _flag_ga_regression(source_row, this_ga, prev_ga):
    """Flag, don't guess (IDENTITY_MATCHING_UPDATE.md Section D): a gestational
    age lower than the previous visit in the same open episode is surfaced for
    the reviewer rather than silently reshuffled."""
    flags = dict(source_row.flags or {})
    flags["gestational_age_weeks"] = {
        "kind": "implausible",
        "message": f"Gestational age {this_ga} wks is lower than the previous visit's {prev_ga} wks in the same pregnancy — check the record.",
    }
    source_row.flags = flags
    source_row.save(update_fields=["flags"])


def _is_referral(value) -> bool:
    if value is None:
        return False
    s = str(value).strip().lower()
    return s not in ("", "no", "none", "n", "nil", "false")


@transaction.atomic
def project_row(source_row) -> dict:
    link = SourceRowLink.objects.filter(source_row=source_row).select_related("woman").first()
    if link is None:
        return {"projected": False, "reason": "unlinked"}
    if _already_projected(source_row):
        return {"projected": False, "reason": "already_projected"}

    woman = link.woman
    facility_id = source_row.intake.facility_id
    family = source_row.intake.register_family
    norm = source_row.normalized or {}
    svc = source_row.service_date or source_row.intake.batch_period_from
    episode = _resolve_episode(woman, facility_id, norm, family, svc)

    common = dict(episode=episode, woman=woman, facility_id=facility_id, source_row=source_row, data=norm)

    if family == "ANC":
        this_ga = _as_int(norm.get("gestational_age_weeks"))
        prev = ANCContact.objects.filter(episode=episode).order_by("-service_date", "-created_at").first()
        if this_ga is not None and prev and prev.gestational_age_weeks is not None and this_ga < prev.gestational_age_weeks:
            _flag_ga_regression(source_row, this_ga, prev.gestational_age_weeks)
        contact_number = ANCContact.objects.filter(episode=episode).count() + 1
        ANCContact.objects.create(
            **common, service_date=svc, contact_number=contact_number,
            gestational_age_weeks=this_ga,
        )
    elif family == "Delivery":
        BirthEvent.objects.create(
            **common,
            delivery_date=_d(norm.get("delivery_date")) or svc,
            delivery_place=norm.get("delivery_place"),
            mode_of_delivery=norm.get("mode_of_delivery"),
            attendant_category=norm.get("attendant_category"),
            maternal_outcome=norm.get("maternal_outcome"),
            baby_outcome=norm.get("baby_outcome"),
            still_birth=norm.get("still_birth"),
            birth_weight_kg=norm.get("birth_weight_kg"),
            baby_sex=norm.get("baby_sex"),
            babies=[{
                "sex": norm.get("baby_sex"),
                "birth_weight_kg": norm.get("birth_weight_kg"),
                "still_birth": norm.get("still_birth"),
                "outcome": norm.get("baby_outcome"),
            }],
            referral_status=norm.get("referral_status"),
        )
        episode.status = EpisodeStatus.DELIVERED
        episode.save(update_fields=["status"])
    elif family == "PNC":
        PNCContact.objects.create(
            **common,
            visit_date=_d(norm.get("visit_date")) or svc,
            days_postpartum=norm.get("days_postpartum"),
            subject=norm.get("subject"),
            feeding_status=norm.get("feeding_status"),
            family_planning=norm.get("family_planning"),
            visit_outcome=norm.get("visit_outcome"),
            referral_status=norm.get("referral_status"),
        )

    if _is_referral(norm.get("referral_status")):
        Referral.objects.create(
            episode=episode, woman=woman, facility_id=facility_id, source_row=source_row,
            origin=family, reason=str(norm.get("referral_status")), date=svc,
            status=Referral.Status.OPEN,
        )

    return {"projected": True, "episode_id": str(episode.id), "family": family}
