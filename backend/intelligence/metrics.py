"""Deterministic maternal metrics (cureva-docs/06 MVP metric set).

Every percentage is returned WITH its numerator and denominator (rule #5). All
date filters use service_date / delivery_date / visit_date (rule #4), never
upload or publish dates. Computed from the projected maternal events, scoped to
a given set of facility ids and a service-date window.

Early-ANC-booking window and the 8-contact target are WHO-aligned defaults; a
country/programme adaptation would be versioned (06 standards baseline).
"""
from maternal_projection.models import (
    ANCContact,
    BirthEvent,
    PNCContact,
    PregnancyEpisode,
    Referral,
)

EARLY_BOOKING_WEEKS = 12  # WHO early-booking window (first trimester)
EIGHT_CONTACT_TARGET = 8


def _ratio(num, den):
    return {"numerator": num, "denominator": den, "rate": round(num / den, 4) if den else None}


def maternal_summary(facility_ids, date_from=None, date_to=None) -> dict:
    """facility_ids: iterable of facility ids (empty => empty picture)."""
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return _empty_summary()

    anc = ANCContact.objects.filter(facility_id__in=facility_ids)
    births = BirthEvent.objects.filter(facility_id__in=facility_ids)
    pnc = PNCContact.objects.filter(facility_id__in=facility_ids)
    refs = Referral.objects.filter(facility_id__in=facility_ids)
    episodes = PregnancyEpisode.objects.filter(facility_id__in=facility_ids)

    if date_from:
        anc = anc.filter(service_date__gte=date_from)
        births = births.filter(delivery_date__gte=date_from)
        pnc = pnc.filter(visit_date__gte=date_from)
        refs = refs.filter(date__gte=date_from)
    if date_to:
        anc = anc.filter(service_date__lte=date_to)
        births = births.filter(delivery_date__lte=date_to)
        pnc = pnc.filter(visit_date__lte=date_to)
        refs = refs.filter(date__lte=date_to)

    # --- Operational ---
    anc_count = anc.count()
    delivery_count = births.count()
    pnc_count = pnc.count()
    open_referrals = refs.filter(status=Referral.Status.OPEN).count()
    closed_referrals = refs.filter(status=Referral.Status.CLOSED).count()

    # --- Early ANC booking ---
    with_booking_ga = episodes.exclude(booking_gestational_age_weeks__isnull=True)
    early = with_booking_ga.filter(booking_gestational_age_weeks__lte=EARLY_BOOKING_WEEKS).count()
    early_booking = _ratio(early, with_booking_ga.count())

    # --- Eight-contact completion (episodes with >=8 ANC contacts) ---
    episode_ids_in_window = set(anc.values_list("episode_id", flat=True))
    contact_counts = {}
    for eid in episode_ids_in_window:
        if eid is not None:
            contact_counts[eid] = ANCContact.objects.filter(episode_id=eid).count()
    eligible_episodes = len(contact_counts)
    eight_plus = sum(1 for n in contact_counts.values() if n >= EIGHT_CONTACT_TARGET)
    four_plus = sum(1 for n in contact_counts.values() if n >= 4)
    eight_contact = _ratio(eight_plus, eligible_episodes)
    four_contact = _ratio(four_plus, eligible_episodes)

    # --- Screening coverage (ANC contacts with any recorded test) ---
    def _has(c, keys):
        d = c.data or {}
        return any(d.get(k) not in (None, "") for k in keys)

    anc_list = list(anc.only("data"))
    screened = sum(1 for c in anc_list if _has(c, ["hiv_result", "syphilis_result", "haemoglobin"]))
    screening = _ratio(screened, len(anc_list))

    # --- Intervention coverage (iron/folate, tetanus, IPTp) ---
    intervened = sum(1 for c in anc_list if _has(c, ["iron_folate_given", "tetanus_given", "iptp_given"]))
    intervention = _ratio(intervened, len(anc_list))

    # --- Referral closure ---
    referral_closure = _ratio(closed_referrals, closed_referrals + open_referrals)

    # --- Delivery linkage (births whose episode has an ANC contact) ---
    linked_deliveries = 0
    for b in births.only("episode_id"):
        if b.episode_id and ANCContact.objects.filter(episode_id=b.episode_id).exists():
            linked_deliveries += 1
    delivery_linkage = _ratio(linked_deliveries, delivery_count)

    # --- Postnatal linkage (birth episodes with a PNC contact) ---
    birth_episode_ids = set(births.values_list("episode_id", flat=True)) - {None}
    with_pnc = sum(1 for eid in birth_episode_ids if PNCContact.objects.filter(episode_id=eid).exists())
    postnatal_linkage = _ratio(with_pnc, len(birth_episode_ids))

    # --- Outcome distribution ---
    live_births = births.filter(still_birth=False).count()
    still_births = births.filter(still_birth=True).count()
    maternal_deaths = births.filter(maternal_outcome__iexact="Died").count()

    return {
        "scope": {"facility_count": len(facility_ids)},
        "operational": {
            "anc_contacts": anc_count,
            "deliveries": delivery_count,
            "pnc_contacts": pnc_count,
            "verified_records": anc_count + delivery_count + pnc_count,
            "open_referrals": open_referrals,
            "closed_referrals": closed_referrals,
        },
        "care_journey": {
            "booked_episodes": episodes.count(),
            "anc_contacts": anc_count,
            "deliveries": delivery_count,
            "pnc_contacts": pnc_count,
            "delivery_linkage": delivery_linkage,
            "postnatal_linkage": postnatal_linkage,
        },
        "metrics": {
            "early_anc_booking": early_booking,
            "four_contact_completion": four_contact,
            "eight_contact_completion": eight_contact,
            "screening_coverage": screening,
            "intervention_coverage": intervention,
            "referral_closure": referral_closure,
        },
        "outcomes": {
            "live_births": live_births,
            "still_births": still_births,
            "maternal_deaths": maternal_deaths,
            "low_birth_weight": births.filter(birth_weight_kg__lt=2.5).exclude(birth_weight_kg__isnull=True).count(),
        },
    }


def _empty_summary():
    zero = _ratio(0, 0)
    return {
        "scope": {"facility_count": 0},
        "operational": {"anc_contacts": 0, "deliveries": 0, "pnc_contacts": 0, "verified_records": 0, "open_referrals": 0, "closed_referrals": 0},
        "care_journey": {"booked_episodes": 0, "anc_contacts": 0, "deliveries": 0, "pnc_contacts": 0, "delivery_linkage": zero, "postnatal_linkage": zero},
        "metrics": {k: zero for k in ["early_anc_booking", "four_contact_completion", "eight_contact_completion", "screening_coverage", "intervention_coverage", "referral_closure"]},
        "outcomes": {"live_births": 0, "still_births": 0, "maternal_deaths": 0, "low_birth_weight": 0},
    }
