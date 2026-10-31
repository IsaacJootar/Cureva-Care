"""Quality-of-care engine (expansion M4).

Goes beyond "did she attend" to "did she get the RIGHT care": each WHO-essential
step of a check-up and delivery, measured as the share of records where it was
done. A re-aggregation of the three registers — same source as every other view.
A blank means "not recorded", which we cannot count as done; so a low score can
mean weak care OR weak recording, and the UI says so plainly.

Each standard's rate = records where the step is recorded as done / relevant
records. The overall score is the average of the standards (0–100). The lowest
standards become the ranked "what to fix" list.
"""
from collections import defaultdict

from identity_access.models import Facility
from maternal_projection.models import ANCContact, BirthEvent

SKILLED = {"doctor", "midwife", "nurse", "skilled", "cho", "community health officer"}

# ANC-visit standards (denominator = ANC contacts).
ANC_STANDARDS = [
    {"key": "bp", "label": "Blood pressure checked", "any": ["blood_pressure"]},
    {"key": "bloodtests", "label": "Blood tests done (HIV, syphilis, anaemia)", "all": ["hiv_result", "syphilis_result", "haemoglobin"]},
    {"key": "iron", "label": "Iron & folate given", "any": ["iron_folate_given"]},
    {"key": "tetanus", "label": "Tetanus vaccine given", "any": ["tetanus_given"]},
    {"key": "malaria", "label": "Malaria prevention given", "any": ["iptp_given"]},
]
# Delivery standards (denominator = births).
BIRTH_STANDARDS = [
    {"key": "sba", "label": "Skilled birth attendant", "kind": "attendant"},
    {"key": "birthweight", "label": "Newborn weighed at birth", "kind": "birthweight"},
]

# Plain next-step for each standard when it's lagging.
ACTIONS = {
    "bp": "Check and record blood pressure at every visit — it catches pre-eclampsia early.",
    "bloodtests": "Make sure HIV, syphilis and anaemia tests are done and recorded at booking.",
    "iron": "Give and record iron & folate at every visit.",
    "tetanus": "Offer and record the tetanus vaccine.",
    "malaria": "Give and record malaria prevention (IPTp) in malaria areas.",
    "sba": "Ensure a skilled provider attends every birth, and record who attended.",
    "birthweight": "Weigh every newborn and record the weight.",
}


def _has_any(data, keys):
    d = data or {}
    return any(d.get(k) not in (None, "") for k in keys)


def _has_all(data, keys):
    d = data or {}
    return all(d.get(k) not in (None, "") for k in keys)


def _skilled(value) -> bool:
    return str(value or "").strip().lower() in SKILLED


def _blank_counts():
    return {s["key"]: {"num": 0, "den": 0} for s in (ANC_STANDARDS + BIRTH_STANDARDS)}


def _accumulate(facility_ids, date_from, date_to):
    """Per-facility standard counts in one pass over ANC + births."""
    acc = defaultdict(_blank_counts)

    anc = ANCContact.objects.filter(facility_id__in=facility_ids)
    if date_from:
        anc = anc.filter(service_date__gte=date_from)
    if date_to:
        anc = anc.filter(service_date__lte=date_to)
    for c in anc.only("facility_id", "data"):
        a = acc[str(c.facility_id)]
        for s in ANC_STANDARDS:
            a[s["key"]]["den"] += 1
            met = _has_all(c.data, s["all"]) if "all" in s else _has_any(c.data, s["any"])
            if met:
                a[s["key"]]["num"] += 1

    births = BirthEvent.objects.filter(facility_id__in=facility_ids)
    if date_from:
        births = births.filter(delivery_date__gte=date_from)
    if date_to:
        births = births.filter(delivery_date__lte=date_to)
    for b in births.only("facility_id", "attendant_category", "birth_weight_kg"):
        a = acc[str(b.facility_id)]
        a["sba"]["den"] += 1
        if _skilled(b.attendant_category):
            a["sba"]["num"] += 1
        a["birthweight"]["den"] += 1
        if b.birth_weight_kg is not None:
            a["birthweight"]["num"] += 1

    return acc


def _rate(num, den):
    return round(num / den, 4) if den else None


def _merge(accs):
    total = _blank_counts()
    for a in accs:
        for k, v in a.items():
            total[k]["num"] += v["num"]
            total[k]["den"] += v["den"]
    return total


def _score(counts):
    """Average of the standards that have any relevant records, as 0–100."""
    rates = [_rate(c["num"], c["den"]) for c in counts.values()]
    rates = [r for r in rates if r is not None]
    return round(sum(rates) / len(rates) * 100) if rates else None


def quality_scorecard(facility_ids, date_from=None, date_to=None) -> dict:
    facility_ids = list(facility_ids or [])
    specs = ANC_STANDARDS + BIRTH_STANDARDS
    if not facility_ids:
        return {"overall_score": None, "standards": [], "by_facility": [], "gaps": []}

    acc = _accumulate(facility_ids, date_from, date_to)
    overall = _merge(acc.values())

    standards = []
    for s in specs:
        c = overall[s["key"]]
        standards.append({
            "key": s["key"], "label": s["label"],
            "numerator": c["num"], "denominator": c["den"], "rate": _rate(c["num"], c["den"]),
        })

    # Gaps: the lagging standards (rate < 0.9), worst first, with a next step.
    gaps = sorted(
        [s for s in standards if s["rate"] is not None and s["rate"] < 0.9],
        key=lambda s: s["rate"],
    )
    for g in gaps:
        g["action"] = ACTIONS.get(g["key"], "")

    facs = {str(f.id): f for f in Facility.objects.filter(id__in=facility_ids).select_related("ward__local_government__state")}
    by_facility = []
    for fid, f in facs.items():
        by_facility.append({
            "facility_id": fid, "name": f.name, "region": f.region_path,
            "score": _score(acc.get(fid, _blank_counts())),
        })
    by_facility.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0)))

    return {
        "overall_score": _score(overall),
        "standards": standards,
        "by_facility": by_facility,
        "gaps": gaps,
    }
