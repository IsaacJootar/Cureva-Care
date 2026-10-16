"""Benchmarking & equity engine (WS2).

Ranks facilities / Wards / LGAs / States on any core metric, and slices the same
metrics by geography and parity band — the single most actionable view for an
NGO or government deciding where to send resources. Everything here is a
re-aggregation of the three registers through the facility hierarchy; no new data
source, every rate carries its numerator/denominator (rule #5), a blank is never
a result (rule #6), and small samples are flagged so a 1/1 = 100% can't outrank a
180/200 = 90%.
"""
from collections import defaultdict

from identity_access.models import Facility
from maternal_projection.models import ANCContact, BirthEvent, PNCContact, PregnancyEpisode, Referral

SMALL_SAMPLE = 5  # rates with a denominator below this are flagged low-confidence

# Metric catalogue: kind + a human label. Rates are shown as %, counts as totals.
METRICS = {
    "deliveries": {"kind": "count", "label": "Deliveries"},
    "anc_contacts": {"kind": "count", "label": "ANC contacts"},
    "pnc_contacts": {"kind": "count", "label": "PNC contacts"},
    "maternal_deaths": {"kind": "count", "label": "Maternal deaths", "invert": True},
    "still_births": {"kind": "count", "label": "Stillbirths", "invert": True},
    "early_anc_booking": {"kind": "rate", "label": "Early ANC booking"},
    "screening_coverage": {"kind": "rate", "label": "Screening coverage"},
    "intervention_coverage": {"kind": "rate", "label": "Intervention coverage"},
    "referral_closure": {"kind": "rate", "label": "Referral closure"},
    "postnatal_linkage": {"kind": "rate", "label": "Postnatal linkage"},
    "low_birth_weight": {"kind": "rate", "label": "Low birth weight", "invert": True},
}

RATE_METRICS = {k for k, m in METRICS.items() if m["kind"] == "rate"}
COUNT_METRICS = {k for k, m in METRICS.items() if m["kind"] == "count"}


def _has(data, keys):
    d = data or {}
    return any(d.get(k) not in (None, "") for k in keys)


def _blank_acc():
    # counts + rate numerators/denominators per group
    return {
        "deliveries": 0, "anc_contacts": 0, "pnc_contacts": 0,
        "maternal_deaths": 0, "still_births": 0,
        "early_num": 0, "early_den": 0,
        "screen_num": 0, "screen_den": 0,
        "interv_num": 0, "interv_den": 0,
        "refc_num": 0, "refc_den": 0,
        "pnc_link_num": 0, "pnc_link_den": 0,
        "lbw_num": 0, "lbw_den": 0,
    }


def _filter_dates(qs, field, date_from, date_to):
    if date_from:
        qs = qs.filter(**{f"{field}__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{field}__lte": date_to})
    return qs


def _accumulate(facility_ids, date_from, date_to):
    """One pass over the registers → per-facility accumulators."""
    acc = defaultdict(_blank_acc)

    anc = _filter_dates(ANCContact.objects.filter(facility_id__in=facility_ids), "service_date", date_from, date_to)
    for c in anc.only("facility_id", "data"):
        a = acc[str(c.facility_id)]
        a["anc_contacts"] += 1
        a["screen_den"] += 1
        if _has(c.data, ["hiv_result", "syphilis_result", "haemoglobin"]):
            a["screen_num"] += 1
        a["interv_den"] += 1
        if _has(c.data, ["iron_folate_given", "tetanus_given", "iptp_given"]):
            a["interv_num"] += 1

    episodes = PregnancyEpisode.objects.filter(facility_id__in=facility_ids).exclude(booking_gestational_age_weeks__isnull=True)
    episodes = _filter_dates(episodes, "booking_date", date_from, date_to)
    for e in episodes.only("facility_id", "booking_gestational_age_weeks"):
        a = acc[str(e.facility_id)]
        a["early_den"] += 1
        if e.booking_gestational_age_weeks <= 12:
            a["early_num"] += 1

    births = _filter_dates(BirthEvent.objects.filter(facility_id__in=facility_ids), "delivery_date", date_from, date_to)
    for b in births.only("facility_id", "still_birth", "maternal_outcome", "birth_weight_kg", "episode_id"):
        a = acc[str(b.facility_id)]
        a["deliveries"] += 1
        if b.still_birth:
            a["still_births"] += 1
        if (b.maternal_outcome or "").lower() == "died":
            a["maternal_deaths"] += 1
        if b.birth_weight_kg is not None:
            a["lbw_den"] += 1
            if float(b.birth_weight_kg) < 2.5:
                a["lbw_num"] += 1
        # postnatal linkage: does this birth's episode have any PNC contact?
        a["pnc_link_den"] += 1
        if b.episode_id and PNCContact.objects.filter(episode_id=b.episode_id).exists():
            a["pnc_link_num"] += 1

    pnc = _filter_dates(PNCContact.objects.filter(facility_id__in=facility_ids), "visit_date", date_from, date_to)
    for p in pnc.only("facility_id"):
        acc[str(p.facility_id)]["pnc_contacts"] += 1

    refs = _filter_dates(Referral.objects.filter(facility_id__in=facility_ids), "date", date_from, date_to)
    for r in refs.only("facility_id", "status"):
        a = acc[str(r.facility_id)]
        a["refc_den"] += 1
        if r.status == Referral.Status.CLOSED:
            a["refc_num"] += 1

    return acc


def _metric_value(a, metric):
    """Return (kind, value_for_ranking, numerator, denominator)."""
    if metric in COUNT_METRICS:
        key = {"deliveries": "deliveries", "anc_contacts": "anc_contacts", "pnc_contacts": "pnc_contacts",
               "maternal_deaths": "maternal_deaths", "still_births": "still_births"}[metric]
        return "count", a[key], a[key], None
    pairs = {
        "early_anc_booking": ("early_num", "early_den"),
        "screening_coverage": ("screen_num", "screen_den"),
        "intervention_coverage": ("interv_num", "interv_den"),
        "referral_closure": ("refc_num", "refc_den"),
        "postnatal_linkage": ("pnc_link_num", "pnc_link_den"),
        "low_birth_weight": ("lbw_num", "lbw_den"),
    }[metric]
    num, den = a[pairs[0]], a[pairs[1]]
    return "rate", (num / den if den else None), num, den


def facility_league(facility_ids, metric="deliveries", date_from=None, date_to=None) -> dict:
    facility_ids = list(facility_ids or [])
    if metric not in METRICS:
        metric = "deliveries"
    if not facility_ids:
        return {"metric": metric, "kind": METRICS[metric]["kind"], "rows": []}

    acc = _accumulate(facility_ids, date_from, date_to)
    facs = {str(f.id): f for f in Facility.objects.filter(id__in=facility_ids).select_related("ward__local_government__state")}
    kind = METRICS[metric]["kind"]
    rows = []
    for fid, f in facs.items():
        a = acc.get(fid, _blank_acc())
        _, value, num, den = _metric_value(a, metric)
        rows.append({
            "facility_id": fid,
            "name": f.name,
            "region": f"{f.ward.local_government.state.name} · {f.ward.local_government.name}",
            "value": value,
            "numerator": num,
            "denominator": den,
            "rate": value if kind == "rate" else None,
            "low_confidence": kind == "rate" and (den or 0) < SMALL_SAMPLE,
        })
    # Rank: counts/rates high→low, except invert metrics (deaths etc.) low→high.
    invert = METRICS[metric].get("invert", False)
    rows.sort(key=lambda r: (r["value"] is None, (r["value"] if r["value"] is not None else 0)), reverse=not invert)
    return {"metric": metric, "kind": kind, "label": METRICS[metric]["label"], "rows": rows}


def geo_rollup(facility_ids, metric="deliveries", level="state", date_from=None, date_to=None) -> dict:
    """Aggregate a metric up to State or LGA for the choropleth / geographic view."""
    facility_ids = list(facility_ids or [])
    if metric not in METRICS:
        metric = "deliveries"
    if level not in ("state", "lga"):
        level = "state"
    if not facility_ids:
        return {"metric": metric, "level": level, "kind": METRICS[metric]["kind"], "areas": []}

    acc = _accumulate(facility_ids, date_from, date_to)
    facs = Facility.objects.filter(id__in=facility_ids).select_related("ward__local_government__state")
    # group facility accumulators by area
    groups = defaultdict(_blank_acc)
    names = {}
    for f in facs:
        if level == "state":
            area_id, area_name = str(f.ward.local_government.state_id), f.ward.local_government.state.name
        else:
            area_id, area_name = str(f.ward.local_government_id), f.ward.local_government.name
        names[area_id] = area_name
        a = acc.get(str(f.id), _blank_acc())
        g = groups[area_id]
        for k in g:
            g[k] += a[k]

    kind = METRICS[metric]["kind"]
    areas = []
    for area_id, g in groups.items():
        _, value, num, den = _metric_value(g, metric)
        areas.append({
            "area_id": area_id, "name": names[area_id],
            "value": value, "numerator": num, "denominator": den,
            "rate": value if kind == "rate" else None,
            "low_confidence": kind == "rate" and (den or 0) < SMALL_SAMPLE,
        })
    areas.sort(key=lambda r: (r["value"] is None, (r["value"] if r["value"] is not None else 0)), reverse=True)
    return {"metric": metric, "level": level, "kind": kind, "label": METRICS[metric]["label"], "areas": areas}


def _parity_band(value):
    try:
        p = int(value)
    except (TypeError, ValueError):
        return None
    if p == 0:
        return "0 (nulliparous)"
    if p <= 4:
        return "1–4"
    return "5+ (grand multipara)"


def equity_by_parity(facility_ids, date_from=None, date_to=None) -> dict:
    """ANC coverage sliced by recorded parity band (unknown parity shown
    separately, never folded into a band — rule #6)."""
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"dimension": "parity", "bands": []}
    anc = _filter_dates(ANCContact.objects.filter(facility_id__in=facility_ids), "service_date", date_from, date_to)
    bands = defaultdict(lambda: {"contacts": 0, "screen_num": 0, "interv_num": 0})
    for c in anc.only("data"):
        band = _parity_band((c.data or {}).get("parity")) or "Unknown"
        b = bands[band]
        b["contacts"] += 1
        if _has(c.data, ["hiv_result", "syphilis_result", "haemoglobin"]):
            b["screen_num"] += 1
        if _has(c.data, ["iron_folate_given", "tetanus_given", "iptp_given"]):
            b["interv_num"] += 1
    order = ["0 (nulliparous)", "1–4", "5+ (grand multipara)", "Unknown"]
    rows = []
    for band in order:
        if band not in bands:
            continue
        b = bands[band]
        rows.append({
            "band": band,
            "contacts": b["contacts"],
            "screening_coverage": {"numerator": b["screen_num"], "denominator": b["contacts"], "rate": round(b["screen_num"] / b["contacts"], 4) if b["contacts"] else None},
            "intervention_coverage": {"numerator": b["interv_num"], "denominator": b["contacts"], "rate": round(b["interv_num"] / b["contacts"], 4) if b["contacts"] else None},
        })
    return {"dimension": "parity", "bands": rows}
