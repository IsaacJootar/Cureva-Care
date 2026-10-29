"""Coverage & reach engine (expansion M1).

Turns recorded register activity into COVERAGE: what share of the women expected
in an area are we actually reaching? Numerators come from the three registers
(same source as every other view); denominators come from admin-loaded
population estimates (CoverageDenominator) — WorldPop / national projections.

Honesty rules (doc 12, principles 2 & 9):
- No denominator for an area → no rate for that area. We never fabricate coverage.
- Every coverage figure is an ESTIMATE; the API returns its source(s) and year so
  the UI can say so plainly.
- Denominators are stored at LGA grain for v1 and rolled up to State.
"""
from collections import defaultdict

from django.db.models import Count

from identity_access.models import Facility
from maternal_projection.models import ANCContact, BirthEvent, PNCContact, PregnancyEpisode

from .models import CoverageDenominator

FOUR_CONTACT = 4

# The four headline coverage indicators and which denominator each divides by.
INDICATORS = {
    "anc1": {"label": "Registered a pregnancy", "denom": "pregnancies"},
    "anc4": {"label": "Had 4+ check-ups", "denom": "pregnancies"},
    "sba": {"label": "Gave birth in a facility", "denom": "births"},
    "pnc": {"label": "Came back after birth", "denom": "births"},
}


def _lga_numerators(facility_ids, date_from, date_to):
    """Per-LGA numerators for the four indicators, plus facility→LGA/State map."""
    facs = list(
        Facility.objects.filter(id__in=facility_ids).select_related(
            "ward__local_government__state"
        )
    )
    fac_lga = {}       # facility_id -> lga_id
    lga_meta = {}      # lga_id -> {"name", "state_id", "state_name"}
    for f in facs:
        lga = f.ward.local_government
        fac_lga[str(f.id)] = str(lga.id)
        lga_meta[str(lga.id)] = {
            "name": lga.name,
            "state_id": str(lga.state_id),
            "state_name": lga.state.name,
        }

    num = defaultdict(lambda: {"anc1": 0, "anc4": 0, "sba": 0, "pnc": 0})

    eps = PregnancyEpisode.objects.filter(facility_id__in=facility_ids)
    if date_from:
        eps = eps.filter(booking_date__gte=date_from)
    if date_to:
        eps = eps.filter(booking_date__lte=date_to)
    eps = list(eps.values("id", "facility_id"))
    ep_ids = [e["id"] for e in eps]
    ep_fac = {e["id"]: str(e["facility_id"]) for e in eps}

    anc_counts = dict(
        ANCContact.objects.filter(episode_id__in=ep_ids)
        .values_list("episode_id")
        .annotate(c=Count("id"))
        .values_list("episode_id", "c")
    )
    for e in eps:
        lga_id = fac_lga.get(str(e["facility_id"]))
        if not lga_id:
            continue
        num[lga_id]["anc1"] += 1
        if anc_counts.get(e["id"], 0) >= FOUR_CONTACT:
            num[lga_id]["anc4"] += 1

    births = BirthEvent.objects.filter(facility_id__in=facility_ids)
    if date_from:
        births = births.filter(delivery_date__gte=date_from)
    if date_to:
        births = births.filter(delivery_date__lte=date_to)
    delivered_eps = set()
    for b in births.values("facility_id", "episode_id"):
        lga_id = fac_lga.get(str(b["facility_id"]))
        if not lga_id:
            continue
        num[lga_id]["sba"] += 1
        if b["episode_id"]:
            delivered_eps.add(b["episode_id"])

    pnc_eps = set(
        PNCContact.objects.filter(episode_id__in=list(delivered_eps))
        .values_list("episode_id", flat=True)
    )
    for ep_id in delivered_eps:
        if ep_id in pnc_eps:
            lga_id = fac_lga.get(ep_fac.get(ep_id, ""))
            if lga_id:
                num[lga_id]["pnc"] += 1

    return num, lga_meta


def _lga_denominators(lga_ids, year):
    """lga_id -> {'pregnancies', 'births', 'source'} for the year (births falls
    back to pregnancies when not separately estimated)."""
    rows = CoverageDenominator.objects.filter(
        area_type=CoverageDenominator.AreaType.LOCAL_GOVERNMENT,
        area_id__in=lga_ids,
        year=year,
    )
    out = {}
    for r in rows:
        preg = r.expected_pregnancies
        births = r.expected_births if r.expected_births is not None else preg
        out[str(r.area_id)] = {"pregnancies": preg, "births": births, "source": r.source}
    return out


def _rate(num, den):
    if not den:
        return None
    return round(num / den, 4)


def coverage(facility_ids, year, level="lga", indicator="anc1", date_from=None, date_to=None) -> dict:
    facility_ids = list(facility_ids or [])
    if indicator not in INDICATORS:
        indicator = "anc1"
    if level not in ("lga", "state"):
        level = "lga"
    if not facility_ids:
        return {"year": year, "level": level, "indicator": indicator, "indicators": {}, "areas": [], "sources": [], "areas_missing_denominator": []}

    num_by_lga, lga_meta = _lga_numerators(facility_ids, date_from, date_to)
    lga_ids = list(lga_meta.keys())
    den_by_lga = _lga_denominators(lga_ids, year)

    # Roll LGA numerators + denominators up to the requested level.
    areas = defaultdict(lambda: {"num": {"anc1": 0, "anc4": 0, "sba": 0, "pnc": 0},
                                 "preg": 0, "births": 0, "has_den": False, "sources": set()})
    names = {}
    for lga_id, meta in lga_meta.items():
        if level == "state":
            area_id, area_name = meta["state_id"], meta["state_name"]
        else:
            area_id, area_name = lga_id, meta["name"]
        names[area_id] = area_name
        a = areas[area_id]
        n = num_by_lga.get(lga_id, {"anc1": 0, "anc4": 0, "sba": 0, "pnc": 0})
        for k in ("anc1", "anc4", "sba", "pnc"):
            a["num"][k] += n[k]
        d = den_by_lga.get(lga_id)
        if d and (d["pregnancies"] or d["births"]):
            a["has_den"] = True
            a["preg"] += d["pregnancies"] or 0
            a["births"] += d["births"] or 0
            if d["source"]:
                a["sources"].add(d["source"])

    # Overall indicators across areas that HAVE a denominator.
    overall = {}
    for key, spec in INDICATORS.items():
        den_field = "preg" if spec["denom"] == "pregnancies" else "births"
        num_total = sum(a["num"][key] for a in areas.values() if a["has_den"])
        den_total = sum(a[den_field] for a in areas.values() if a["has_den"])
        overall[key] = {
            "label": spec["label"],
            "numerator": num_total,
            "denominator": den_total or None,
            "rate": _rate(num_total, den_total),
        }

    # Per-area breakdown for the selected indicator (map + league table).
    den_field = "preg" if INDICATORS[indicator]["denom"] == "pregnancies" else "births"
    area_rows = []
    missing = []
    for area_id, a in areas.items():
        n = a["num"][indicator]
        den = a[den_field] if a["has_den"] else None
        if not a["has_den"]:
            missing.append(names[area_id])
        area_rows.append({
            "area_id": area_id,
            "name": names[area_id],
            "numerator": n,
            "denominator": den,
            "rate": _rate(n, den) if den else None,
            "has_denominator": a["has_den"],
        })
    area_rows.sort(key=lambda r: (r["rate"] is None, -(r["rate"] or 0)))

    sources = sorted({s for a in areas.values() for s in a["sources"]})
    return {
        "year": year,
        "level": level,
        "indicator": indicator,
        "indicators": overall,
        "areas": area_rows,
        "sources": sources,
        "areas_missing_denominator": sorted(missing),
    }
