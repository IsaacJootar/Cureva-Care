"""Daily facility metric aggregation — idempotent rebuild from maternal events.

Re-runnable without double counting: a rebuild deletes the facility's existing
daily rows and recomputes them from the projected events, so publishing twice
(or re-confirming) never inflates the aggregates (cureva-docs/04 performance).
"""
from collections import defaultdict

from django.db import transaction

from .models import DailyFacilityMetric


@transaction.atomic
def rebuild_facility_metrics(facility_id) -> int:
    from maternal_projection.models import ANCContact, BirthEvent, PNCContact, Referral

    DailyFacilityMetric.objects.filter(facility_id=facility_id).delete()

    buckets: dict = defaultdict(lambda: {
        "anc_contacts": 0, "deliveries": 0, "pnc_contacts": 0,
        "open_referrals": 0, "closed_referrals": 0, "live_births": 0, "still_births": 0,
    })

    for c in ANCContact.objects.filter(facility_id=facility_id).only("service_date"):
        if c.service_date:
            buckets[c.service_date]["anc_contacts"] += 1

    for b in BirthEvent.objects.filter(facility_id=facility_id).only("delivery_date", "still_birth"):
        if b.delivery_date:
            buckets[b.delivery_date]["deliveries"] += 1
            if b.still_birth:
                buckets[b.delivery_date]["still_births"] += 1
            else:
                buckets[b.delivery_date]["live_births"] += 1

    for p in PNCContact.objects.filter(facility_id=facility_id).only("visit_date"):
        if p.visit_date:
            buckets[p.visit_date]["pnc_contacts"] += 1

    for r in Referral.objects.filter(facility_id=facility_id).only("date", "status"):
        if r.date:
            key = "closed_referrals" if r.status == Referral.Status.CLOSED else "open_referrals"
            buckets[r.date][key] += 1

    rows = [
        DailyFacilityMetric(facility_id=facility_id, day=day, **counts)
        for day, counts in buckets.items()
    ]
    DailyFacilityMetric.objects.bulk_create(rows)
    return len(rows)
