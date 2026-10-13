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


def _resolve_episode(woman, facility_id, norm, family):
    lmp = _d(norm.get("lmp"))
    if family == "ANC" and lmp:
        ep = PregnancyEpisode.objects.filter(woman=woman, lmp=lmp).first()
        if ep:
            return ep
        return _create_episode(woman, facility_id, norm)
    ep = PregnancyEpisode.objects.filter(woman=woman).order_by("-created_at").first()
    return ep or _create_episode(woman, facility_id, norm)


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
    episode = _resolve_episode(woman, facility_id, norm, family)

    common = dict(episode=episode, woman=woman, facility_id=facility_id, source_row=source_row, data=norm)

    if family == "ANC":
        contact_number = ANCContact.objects.filter(episode=episode).count() + 1
        ANCContact.objects.create(
            **common, service_date=svc, contact_number=contact_number,
            gestational_age_weeks=norm.get("gestational_age_weeks"),
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
