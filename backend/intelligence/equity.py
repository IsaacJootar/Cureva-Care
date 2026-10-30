"""Equity engine (expansion M6) — "who is being left behind".

Slices a coverage metric by sub-group (number of past births, mother's age, or
area) and surfaces the equity GAP between the best- and worst-served groups, so
a programme can see where care is systematically unequal. A re-aggregation of
the ANC register — same source as every other view; a blank is never a result,
and small groups are flagged so a 1/1 = 100% can't masquerade as a real gap.
"""
from collections import defaultdict

from identity_access.models import Facility
from maternal_projection.models import ANCContact

SMALL_SAMPLE = 5

DIMENSIONS = {
    "parity": "By number of past births",
    "age": "By mother's age",
    "area": "By area (LGA)",
}
METRICS = {
    "screening": {"label": "Tested (HIV, syphilis, anaemia)", "fields": ["hiv_result", "syphilis_result", "haemoglobin"]},
    "intervention": {"label": "Got preventives (iron, tetanus, malaria)", "fields": ["iron_folate_given", "tetanus_given", "iptp_given"]},
}

_PARITY_ORDER = ["First pregnancy (0 past births)", "1–4 past births", "5+ past births", "Unknown"]
_AGE_ORDER = ["Under 20", "20–34", "35 or older", "Unknown"]


def _has(data, keys):
    d = data or {}
    return any(d.get(k) not in (None, "") for k in keys)


def _parity_band(value):
    try:
        p = int(value)
    except (TypeError, ValueError):
        return "Unknown"
    if p == 0:
        return "First pregnancy (0 past births)"
    if p <= 4:
        return "1–4 past births"
    return "5+ past births"


def _age_band(age):
    try:
        a = int(age)
    except (TypeError, ValueError):
        return "Unknown"
    if a < 20:
        return "Under 20"
    if a <= 34:
        return "20–34"
    return "35 or older"


def equity_breakdown(facility_ids, dimension="parity", metric="screening", date_from=None, date_to=None) -> dict:
    facility_ids = list(facility_ids or [])
    if dimension not in DIMENSIONS:
        dimension = "parity"
    if metric not in METRICS:
        metric = "screening"
    base = {
        "dimension": dimension,
        "metric": metric,
        "metric_label": METRICS[metric]["label"],
        "dimensions": [{"key": k, "label": v} for k, v in DIMENSIONS.items()],
        "metrics": [{"key": k, "label": v["label"]} for k, v in METRICS.items()],
        "groups": [],
        "gap": None,
    }
    if not facility_ids:
        return base

    fields = METRICS[metric]["fields"]
    lga_of = {}
    if dimension == "area":
        for f in Facility.objects.filter(id__in=facility_ids).select_related("ward__local_government"):
            lga_of[str(f.id)] = f.ward.local_government.name

    qs = ANCContact.objects.filter(facility_id__in=facility_ids)
    if date_from:
        qs = qs.filter(service_date__gte=date_from)
    if date_to:
        qs = qs.filter(service_date__lte=date_to)
    if dimension == "age":
        qs = qs.select_related("woman")

    groups = defaultdict(lambda: {"num": 0, "den": 0})
    for c in qs:
        if dimension == "parity":
            g = _parity_band((c.data or {}).get("parity"))
        elif dimension == "age":
            g = _age_band(c.woman.age if c.woman_id else None)
        else:
            g = lga_of.get(str(c.facility_id), "Unknown")
        grp = groups[g]
        grp["den"] += 1
        if _has(c.data, fields):
            grp["num"] += 1

    rows = []
    for name, g in groups.items():
        rate = round(g["num"] / g["den"], 4) if g["den"] else None
        rows.append({
            "group": name, "numerator": g["num"], "denominator": g["den"],
            "rate": rate, "low_confidence": g["den"] < SMALL_SAMPLE,
        })

    # Order: fixed band order for parity/age; by coverage (worst first) for area.
    if dimension == "parity":
        rows.sort(key=lambda r: _PARITY_ORDER.index(r["group"]) if r["group"] in _PARITY_ORDER else 99)
    elif dimension == "age":
        rows.sort(key=lambda r: _AGE_ORDER.index(r["group"]) if r["group"] in _AGE_ORDER else 99)
    else:
        rows.sort(key=lambda r: (r["rate"] is None, r["rate"] or 0))

    # Equity gap: best vs worst among real groups with an adequate sample.
    # "Unknown" is the missing-data catch-all, never a comparison group.
    adequate = [r for r in rows if not r["low_confidence"] and r["rate"] is not None and r["group"] != "Unknown"]
    base["comparable_groups"] = len(adequate)
    if len(adequate) >= 2:
        best = max(adequate, key=lambda r: r["rate"])
        worst = min(adequate, key=lambda r: r["rate"])
        points = round((best["rate"] - worst["rate"]) * 100, 1)
        # Only a real gap: different groups, and an actual difference.
        if best["group"] != worst["group"] and points > 0:
            base["gap"] = {
                "best": best["group"], "best_rate": best["rate"],
                "worst": worst["group"], "worst_rate": worst["rate"],
                "points": points,
            }

    base["groups"] = rows
    return base
