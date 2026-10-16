"""Continuum & cohort engine (WS3).

The flagship "who fell through" view. The care funnel counts women at each step of
the continuum (booked → 4+ ANC → 8+ ANC → delivered → postnatal) and exposes the
DROP-OFF at each step as an access-scoped, downloadable line-list of named women
to follow up. Cohort retention follows each booking-month cohort through the
continuum over time.

Linkage rule (02-data-model.md): only linked episodes contribute to a
cross-register step; an unlinked encounter still counts operationally elsewhere.
Access rule (07): woman-level line-lists are gated — aggregate tier gets counts
only, de-identified strips the name, identifiable sees the woman.
"""
from collections import Counter, defaultdict
from datetime import date

from django.db.models import Count

from identity_access.models import AccessLevel
from maternal_projection.models import ANCContact, BirthEvent, PNCContact, PregnancyEpisode

FOUR_CONTACT = 4
EIGHT_CONTACT = 8


def _episode_stats(facility_ids, date_from=None, date_to=None):
    """Return episodes (list) + helper maps: anc count, delivered set, pnc set."""
    eps = PregnancyEpisode.objects.filter(facility_id__in=facility_ids).select_related("woman")
    if date_from:
        eps = eps.filter(booking_date__gte=date_from)
    if date_to:
        eps = eps.filter(booking_date__lte=date_to)
    eps = list(eps)
    ep_ids = [e.id for e in eps]

    anc_counts = dict(
        ANCContact.objects.filter(episode_id__in=ep_ids).values_list("episode_id").annotate(c=Count("id")).values_list("episode_id", "c")
    )
    delivered = {}
    for b in BirthEvent.objects.filter(episode_id__in=ep_ids).values("episode_id", "delivery_date"):
        delivered[b["episode_id"]] = b["delivery_date"]
    pnc_eps = set(PNCContact.objects.filter(episode_id__in=ep_ids).values_list("episode_id", flat=True))
    return eps, anc_counts, delivered, pnc_eps


def care_funnel(facility_ids, date_from=None, date_to=None) -> dict:
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"steps": [], "total": 0}
    eps, anc_counts, delivered, pnc_eps = _episode_stats(facility_ids, date_from, date_to)

    booked = len(eps)
    anc4 = sum(1 for e in eps if anc_counts.get(e.id, 0) >= FOUR_CONTACT)
    anc8 = sum(1 for e in eps if anc_counts.get(e.id, 0) >= EIGHT_CONTACT)
    delivered_n = sum(1 for e in eps if e.id in delivered)
    pnc_n = sum(1 for e in eps if e.id in delivered and e.id in pnc_eps)

    raw = [
        ("Booked", booked),
        ("4+ ANC contacts", anc4),
        ("8+ ANC contacts", anc8),
        ("Delivered", delivered_n),
        ("Postnatal contact", pnc_n),
    ]
    steps = []
    for i, (label, value) in enumerate(raw):
        prev = raw[i - 1][1] if i > 0 else value
        steps.append({
            "label": label,
            "value": value,
            "drop_from_previous": max(0, prev - value) if i > 0 else 0,
            "share_of_booked": round(value / booked, 4) if booked else None,
        })
    return {"steps": steps, "total": booked}


# Drop-off list definitions: each returns the episodes that fell out at a step.
DROPOFFS = {
    "anc_under_4": "Booked but fewer than 4 ANC contacts",
    "booked_no_delivery": "Booked but no delivery recorded",
    "delivered_no_pnc": "Delivered but no postnatal contact",
}


def dropoff_lines(facility_ids, kind, access_level, date_from=None, date_to=None, limit=500) -> dict:
    facility_ids = list(facility_ids or [])
    if kind not in DROPOFFS:
        kind = "delivered_no_pnc"
    if not facility_ids:
        return {"kind": kind, "label": DROPOFFS[kind], "count": 0, "rows": []}
    eps, anc_counts, delivered, pnc_eps = _episode_stats(facility_ids, date_from, date_to)

    def matches(e):
        if kind == "anc_under_4":
            return anc_counts.get(e.id, 0) < FOUR_CONTACT and e.id not in delivered
        if kind == "booked_no_delivery":
            # overdue: booked and no delivery (a booking with no recorded outcome)
            return e.id not in delivered
        if kind == "delivered_no_pnc":
            return e.id in delivered and e.id not in pnc_eps
        return False

    matched = [e for e in eps if matches(e)]
    count = len(matched)

    # Aggregate tier: counts only, never the women.
    if access_level == AccessLevel.AGGREGATE:
        return {"kind": kind, "label": DROPOFFS[kind], "count": count, "rows": [], "access_level": access_level}

    de_identify = access_level == AccessLevel.DE_IDENTIFIED
    rows = []
    for e in matched[:limit]:
        last_date = delivered.get(e.id) or e.booking_date
        days_since = (date.today() - last_date).days if last_date else None
        rows.append({
            "episode_id": str(e.id),
            "woman": None if de_identify else {"internal_id": e.woman.internal_id, "name": e.woman.name},
            "woman_internal_id": e.woman.internal_id,
            "booking_date": e.booking_date,
            "anc_contacts": anc_counts.get(e.id, 0),
            "delivered_on": delivered.get(e.id),
            "days_since": days_since,
        })
    rows.sort(key=lambda r: (r["days_since"] is None, -(r["days_since"] or 0)))
    return {"kind": kind, "label": DROPOFFS[kind], "count": count, "rows": rows, "access_level": access_level}


def cohort_retention(facility_ids, date_from=None, date_to=None) -> dict:
    """By booking-month cohort: share reaching 4+ ANC, delivery, and PNC."""
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"cohorts": [], "series": {}}
    eps, anc_counts, delivered, pnc_eps = _episode_stats(facility_ids, date_from, date_to)

    booked_by = Counter()
    anc4_by, deliv_by, pnc_by = defaultdict(int), defaultdict(int), defaultdict(int)
    for e in eps:
        if not e.booking_date:
            continue
        key = f"{e.booking_date.year}-{e.booking_date.month:02d}"
        booked_by[key] += 1
        if anc_counts.get(e.id, 0) >= FOUR_CONTACT:
            anc4_by[key] += 1
        if e.id in delivered:
            deliv_by[key] += 1
        if e.id in delivered and e.id in pnc_eps:
            pnc_by[key] += 1

    cohorts = sorted(booked_by)

    def rate_points(num_by):
        return [
            {"x": c, "numerator": num_by.get(c, 0), "denominator": booked_by[c],
             "rate": round(num_by.get(c, 0) / booked_by[c], 4) if booked_by[c] else None}
            for c in cohorts
        ]

    return {
        "cohorts": cohorts,
        "series": {
            "anc4": {"label": "Reached 4+ ANC", "points": rate_points(anc4_by)},
            "delivered": {"label": "Delivered", "points": rate_points(deliv_by)},
            "pnc": {"label": "Postnatal contact", "points": rate_points(pnc_by)},
        },
    }
