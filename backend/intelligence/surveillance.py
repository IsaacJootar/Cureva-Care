"""MPDSR-grade severe-outcome surveillance (WS4).

Every stillbirth, maternal death, and early neonatal death becomes a traceable
CASE that carries its linked antenatal→delivery→postnatal story — because the
identity linkage already ties one woman's ANC, Delivery and PNC rows together.
This is the continuous, linked death surveillance that MPDSR mandates, generated
from the registers rather than assembled by hand.

Nothing is inferred (rule #6): a case exists only where a severe outcome is
RECORDED on the delivery register. Case-level data is access-scoped (rule #7):
aggregate tier gets counts/trend/clusters only, de-identified hides the name.
"""
from collections import Counter, defaultdict
from datetime import date
import re

from identity_access.models import AccessLevel
from maternal_projection.models import ANCContact, BirthEvent, PNCContact


def _severe_types(b) -> list[str]:
    types = []
    if b.still_birth or (b.baby_outcome or "").lower() == "stillbirth":
        types.append("Stillbirth")
    if (b.baby_outcome or "").lower() == "early neonatal death":
        types.append("Newborn death (first 7 days)")
    if (b.maternal_outcome or "").lower() == "died":
        types.append("Mother died")
    return types


def _bp_high(value) -> bool:
    m = re.match(r"\s*(\d+)\s*/\s*(\d+)", str(value or ""))
    return bool(m) and (int(m.group(1)) >= 140 or int(m.group(2)) >= 90)


def _antenatal_risk(episode_id) -> list[str]:
    """Recorded antenatal risk markers on the linked ANC contacts."""
    flags = set()
    for c in ANCContact.objects.filter(episode_id=episode_id).only("data"):
        d = c.data or {}
        if _bp_high(d.get("blood_pressure")):
            flags.add("Raised BP")
        hb = d.get("haemoglobin")
        try:
            if hb is not None and float(hb) < 11:
                flags.add("Anaemia")
        except (TypeError, ValueError):
            pass
        if (d.get("genotype") or "").upper() in ("SS", "SC"):
            flags.add("Sickle-cell")
        if str(d.get("hiv_result") or "").lower() in ("positive", "reactive", "pos"):
            flags.add("HIV+")
        if str(d.get("syphilis_result") or "").lower() in ("positive", "reactive", "pos"):
            flags.add("Syphilis+")
    return sorted(flags)


def _severe_births(facility_ids, date_from, date_to):
    qs = BirthEvent.objects.filter(facility_id__in=facility_ids).select_related("woman", "facility__ward__local_government__state")
    if date_from:
        qs = qs.filter(delivery_date__gte=date_from)
    if date_to:
        qs = qs.filter(delivery_date__lte=date_to)
    return [b for b in qs if _severe_types(b)]


def severe_cases(facility_ids, access_level, date_from=None, date_to=None, limit=500) -> dict:
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"count": 0, "cases": []}
    severe = _severe_births(facility_ids, date_from, date_to)
    count = len(severe)
    by_type = Counter()
    for b in severe:
        for t in _severe_types(b):
            by_type[t] += 1

    if access_level == AccessLevel.AGGREGATE:
        return {"count": count, "by_type": dict(by_type), "cases": [], "access_level": access_level}

    de_identify = access_level == AccessLevel.DE_IDENTIFIED
    cases = []
    for b in severe[:limit]:
        f = b.facility
        cases.append({
            "episode_id": str(b.episode_id) if b.episode_id else None,
            "birth_event_id": str(b.id),
            "woman": None if de_identify else {"internal_id": b.woman.internal_id, "name": b.woman.name},
            "woman_internal_id": b.woman.internal_id,
            "facility": f.name,
            "region": f.region_path,
            "delivery_date": b.delivery_date,
            "outcomes": _severe_types(b),
            "antenatal_risk": _antenatal_risk(b.episode_id) if b.episode_id else [],
            "mode_of_delivery": b.mode_of_delivery,
            "attendant": b.attendant_category,
        })
    cases.sort(key=lambda c: (c["delivery_date"] is None, c["delivery_date"] or date.min), reverse=True)
    return {"count": count, "by_type": dict(by_type), "cases": cases, "access_level": access_level}


def case_timeline(episode_id, facility_ids, access_level) -> dict:
    """The woman's full linked story: ANC contacts → delivery → PNC contacts."""
    facility_ids = list(facility_ids or [])
    events = []
    anc = ANCContact.objects.filter(episode_id=episode_id, facility_id__in=facility_ids).order_by("service_date")
    for c in anc:
        d = c.data or {}
        detail = []
        if d.get("gestational_age_weeks"):
            detail.append(f"GA {d['gestational_age_weeks']} wks")
        if d.get("blood_pressure"):
            detail.append(f"BP {d['blood_pressure']}{' ⚠' if _bp_high(d.get('blood_pressure')) else ''}")
        if d.get("haemoglobin"):
            detail.append(f"Hb {d['haemoglobin']}")
        events.append({"date": c.service_date, "type": "ANC", "summary": ", ".join(detail) or "ANC contact"})
    for b in BirthEvent.objects.filter(episode_id=episode_id, facility_id__in=facility_ids):
        parts = [p for p in [b.mode_of_delivery, b.delivery_place, b.maternal_outcome and f"mother: {b.maternal_outcome}", b.baby_outcome and f"baby: {b.baby_outcome}"] if p]
        events.append({"date": b.delivery_date, "type": "Delivery", "summary": ", ".join(parts) or "Delivery", "severe": _severe_types(b)})
    for p in PNCContact.objects.filter(episode_id=episode_id, facility_id__in=facility_ids).order_by("visit_date"):
        d = p.data or {}
        parts = [x for x in [p.subject and f"{p.subject}", d.get("danger_signs") and f"danger: {d['danger_signs']}", p.visit_outcome] if x]
        events.append({"date": p.visit_date, "type": "PNC", "summary": ", ".join(parts) or "PNC visit"})
    events.sort(key=lambda e: (e["date"] is None, e["date"] or date.min))
    return {"episode_id": str(episode_id), "events": events}


def severe_trend(facility_ids, date_from=None, date_to=None, bucket="month") -> dict:
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"buckets": [], "series": {}}
    severe = _severe_births(facility_ids, date_from, date_to)

    def key(d):
        return f"{d.year}-{d.month:02d}" if d else None

    by = defaultdict(lambda: Counter())
    for b in severe:
        k = key(b.delivery_date)
        if k is None:
            continue
        for t in _severe_types(b):
            by[k][t] += 1
    buckets = sorted(by)
    types = ["Stillbirth", "Newborn death (first 7 days)", "Mother died"]
    series = {t: [{"x": bkt, "value": by[bkt].get(t, 0)} for bkt in buckets] for t in types}
    return {"buckets": buckets, "series": series}


def facility_clusters(facility_ids, date_from=None, date_to=None) -> dict:
    """Per-facility severe-outcome count and rate (severe / deliveries), ranked —
    an early signal of a facility that needs a closer look."""
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"facilities": []}
    severe = _severe_births(facility_ids, date_from, date_to)
    severe_by = Counter(str(b.facility_id) for b in severe)
    deliv_by = Counter()
    qs = BirthEvent.objects.filter(facility_id__in=facility_ids)
    if date_from:
        qs = qs.filter(delivery_date__gte=date_from)
    if date_to:
        qs = qs.filter(delivery_date__lte=date_to)
    for fid in qs.values_list("facility_id", flat=True):
        deliv_by[str(fid)] += 1

    from identity_access.models import Facility
    facs = {str(f.id): f for f in Facility.objects.filter(id__in=facility_ids).select_related("ward__local_government__state")}
    rows = []
    for fid, f in facs.items():
        sev, deliv = severe_by.get(fid, 0), deliv_by.get(fid, 0)
        if sev == 0 and deliv == 0:
            continue
        rows.append({
            "facility_id": fid, "name": f.name,
            "region": f.region_path,
            "severe": sev, "deliveries": deliv,
            "rate": round(sev / deliv, 4) if deliv else None,
        })
    rows.sort(key=lambda r: (r["rate"] is None, -(r["rate"] or 0), -r["severe"]))
    return {"facilities": rows}
