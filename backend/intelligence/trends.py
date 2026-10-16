"""Time-bucketed trends for the intelligence module (WS1).

Turns the point-in-time metrics into time series: every datable maternal event
is bucketed by its own service date (never upload/publish date — rule #4), by
month or ISO week, and each metric is returned per bucket WITH its
numerator/denominator (rule #5). A blank is never counted as a result (rule #6).

Count series answer "how much activity"; rate series answer "what share", each
with denominators so a low count can't masquerade as a high rate. Deltas compare
the latest complete bucket to the one before it.
"""
from collections import defaultdict
from datetime import date

from maternal_projection.models import ANCContact, BirthEvent, PNCContact, PregnancyEpisode, Referral


def _bucket_key(d: date, bucket: str) -> str:
    if d is None:
        return None
    if bucket == "week":
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    return f"{d.year}-{d.month:02d}"


def _ordered_buckets(dates: list, bucket: str) -> list[str]:
    keys = sorted({_bucket_key(d, bucket) for d in dates if d is not None})
    return keys


def _has(data, keys):
    d = data or {}
    return any(d.get(k) not in (None, "") for k in keys)


def _rate_points(buckets, num_by, den_by):
    pts = []
    for b in buckets:
        num, den = num_by.get(b, 0), den_by.get(b, 0)
        pts.append({"x": b, "numerator": num, "denominator": den, "rate": round(num / den, 4) if den else None})
    return pts


def _count_points(buckets, by):
    return [{"x": b, "value": by.get(b, 0)} for b in buckets]


def compute_trends(facility_ids, date_from=None, date_to=None, bucket="month") -> dict:
    facility_ids = list(facility_ids or [])
    if bucket not in ("month", "week"):
        bucket = "month"
    if not facility_ids:
        return {"bucket": bucket, "buckets": [], "metrics": {}, "deltas": {}}

    anc = ANCContact.objects.filter(facility_id__in=facility_ids)
    births = BirthEvent.objects.filter(facility_id__in=facility_ids)
    pnc = PNCContact.objects.filter(facility_id__in=facility_ids)
    refs = Referral.objects.filter(facility_id__in=facility_ids)
    episodes = PregnancyEpisode.objects.filter(facility_id__in=facility_ids).exclude(booking_date__isnull=True)

    if date_from:
        anc = anc.filter(service_date__gte=date_from)
        births = births.filter(delivery_date__gte=date_from)
        pnc = pnc.filter(visit_date__gte=date_from)
        refs = refs.filter(date__gte=date_from)
        episodes = episodes.filter(booking_date__gte=date_from)
    if date_to:
        anc = anc.filter(service_date__lte=date_to)
        births = births.filter(delivery_date__lte=date_to)
        pnc = pnc.filter(visit_date__lte=date_to)
        refs = refs.filter(date__lte=date_to)
        episodes = episodes.filter(booking_date__lte=date_to)

    anc = list(anc.only("service_date", "data"))
    births = list(births.only("delivery_date", "still_birth", "maternal_outcome", "birth_weight_kg"))
    pnc = list(pnc.only("visit_date", "data"))
    refs = list(refs.only("date", "status"))
    episodes = list(episodes.only("booking_date", "booking_gestational_age_weeks"))

    all_dates = (
        [c.service_date for c in anc]
        + [b.delivery_date for b in births]
        + [p.visit_date for p in pnc]
        + [r.date for r in refs]
        + [e.booking_date for e in episodes]
    )
    buckets = _ordered_buckets(all_dates, bucket)

    # --- Count accumulators ---
    anc_by, deliv_by, pnc_by = defaultdict(int), defaultdict(int), defaultdict(int)
    live_by, still_by, mdeath_by = defaultdict(int), defaultdict(int), defaultdict(int)
    # --- Rate accumulators (num/den) ---
    screen_num, screen_den = defaultdict(int), defaultdict(int)
    interv_num, interv_den = defaultdict(int), defaultdict(int)
    early_num, early_den = defaultdict(int), defaultdict(int)
    lbw_num, lbw_den = defaultdict(int), defaultdict(int)
    refc_num, refc_den = defaultdict(int), defaultdict(int)

    for c in anc:
        b = _bucket_key(c.service_date, bucket)
        if b is None:
            continue
        anc_by[b] += 1
        screen_den[b] += 1
        if _has(c.data, ["hiv_result", "syphilis_result", "haemoglobin"]):
            screen_num[b] += 1
        interv_den[b] += 1
        if _has(c.data, ["iron_folate_given", "tetanus_given", "iptp_given"]):
            interv_num[b] += 1

    for e in episodes:
        b = _bucket_key(e.booking_date, bucket)
        if b is None or e.booking_gestational_age_weeks is None:
            continue
        early_den[b] += 1
        if e.booking_gestational_age_weeks <= 12:
            early_num[b] += 1

    for bi in births:
        b = _bucket_key(bi.delivery_date, bucket)
        if b is None:
            continue
        deliv_by[b] += 1
        if bi.still_birth:
            still_by[b] += 1
        else:
            live_by[b] += 1
        if (bi.maternal_outcome or "").lower() == "died":
            mdeath_by[b] += 1
        if bi.birth_weight_kg is not None:
            lbw_den[b] += 1
            if float(bi.birth_weight_kg) < 2.5:
                lbw_num[b] += 1

    for p in pnc:
        b = _bucket_key(p.visit_date, bucket)
        if b is not None:
            pnc_by[b] += 1

    for r in refs:
        b = _bucket_key(r.date, bucket)
        if b is None:
            continue
        refc_den[b] += 1
        if r.status == Referral.Status.CLOSED:
            refc_num[b] += 1

    metrics = {
        "anc_contacts": {"kind": "count", "label": "ANC contacts", "points": _count_points(buckets, anc_by)},
        "deliveries": {"kind": "count", "label": "Deliveries", "points": _count_points(buckets, deliv_by)},
        "pnc_contacts": {"kind": "count", "label": "PNC contacts", "points": _count_points(buckets, pnc_by)},
        "live_births": {"kind": "count", "label": "Live births", "points": _count_points(buckets, live_by)},
        "still_births": {"kind": "count", "label": "Stillbirths", "points": _count_points(buckets, still_by), "invert": True},
        "maternal_deaths": {"kind": "count", "label": "Maternal deaths", "points": _count_points(buckets, mdeath_by), "invert": True},
        "early_anc_booking": {"kind": "rate", "label": "Early ANC booking", "points": _rate_points(buckets, early_num, early_den)},
        "screening_coverage": {"kind": "rate", "label": "Screening coverage", "points": _rate_points(buckets, screen_num, screen_den)},
        "intervention_coverage": {"kind": "rate", "label": "Intervention coverage", "points": _rate_points(buckets, interv_num, interv_den)},
        "referral_closure": {"kind": "rate", "label": "Referral closure", "points": _rate_points(buckets, refc_num, refc_den)},
        "low_birth_weight": {"kind": "rate", "label": "Low birth weight", "points": _rate_points(buckets, lbw_num, lbw_den), "invert": True},
    }

    deltas = {}
    for key, m in metrics.items():
        pts = m["points"]
        if len(pts) < 2:
            deltas[key] = None
            continue
        cur, prev = pts[-1], pts[-2]
        if m["kind"] == "count":
            deltas[key] = cur["value"] - prev["value"]
        else:
            if cur["rate"] is None or prev["rate"] is None:
                deltas[key] = None
            else:
                deltas[key] = round((cur["rate"] - prev["rate"]) * 100)  # percentage points

    return {"bucket": bucket, "buckets": buckets, "metrics": metrics, "deltas": deltas}
