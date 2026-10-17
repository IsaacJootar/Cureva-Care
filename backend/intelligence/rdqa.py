"""RDQA-as-a-service (WS6).

A continuous Routine Data Quality Assessment — the periodic site-visit audit that
donors (PEPFAR, Global Fund) require as a grant condition, generated continuously
from the intake pipeline instead of once a year by a consultant. Per facility it
reports extraction confidence, completeness, implausible-value rate, open template
flags, and timeliness, plus a transparent composite score with its components
shown. Every number traces to pipeline metadata on the three registers.
"""
from collections import defaultdict

from register_intake.models import IntakeStatus, SourceRow, SourceRowStatus, TemplateFlag
from register_intake.resolution import resolve_template


def _template_cols(facility_id, family, cache):
    key = (facility_id, family)
    if key not in cache:
        try:
            cache[key] = len(resolve_template(family, facility_id).schema.get("columns", []))
        except Exception:
            cache[key] = 0
    return cache[key]


def _facility_rdqa(rows, open_flags, tmpl_cache):
    conf_values = []
    nonempty = 0
    expected = 0
    implausible_rows = 0
    timeliness = []
    n = 0
    for r in rows:
        n += 1
        conf_values.extend(v for v in (r.extraction_confidence or {}).values() if isinstance(v, (int, float)))
        norm = r.normalized or {}
        nonempty += sum(1 for v in norm.values() if v not in (None, ""))
        expected += _template_cols(r.intake.facility_id, r.intake.register_family, tmpl_cache) or len(norm) or 1
        flags = r.flags or {}
        if any((info or {}).get("kind") in ("implausible", "type_error") for info in flags.values()):
            implausible_rows += 1
        if r.intake.published_at and r.intake.batch_period_to:
            timeliness.append((r.intake.published_at.date() - r.intake.batch_period_to).days)

    avg_conf = round(sum(conf_values) / len(conf_values), 3) if conf_values else None
    completeness = round(nonempty / expected, 3) if expected else None
    implausible_rate = round(implausible_rows / n, 3) if n else None
    avg_timeliness = round(sum(timeliness) / len(timeliness), 1) if timeliness else None

    # Composite 0-100: confidence + completeness, penalised by implausible rate
    # and open flags. Transparent; weights are not clinical.
    conf_c = (avg_conf or 0) * 100
    comp_c = (completeness or 0) * 100
    impl_pen = (implausible_rate or 0) * 100
    flag_pen = min(open_flags * 2, 20)
    score = max(0, round(0.45 * conf_c + 0.45 * comp_c - 0.10 * impl_pen - flag_pen))
    return {
        "rows": n,
        "avg_extraction_confidence": avg_conf,
        "completeness": completeness,
        "implausible_rate": implausible_rate,
        "open_template_flags": open_flags,
        "avg_days_to_publish": avg_timeliness,
        "score": score if n else None,
    }


def rdqa_scorecard(facility_ids, date_from=None, date_to=None) -> dict:
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"facilities": [], "overall": {}}

    from identity_access.models import Facility

    qs = SourceRow.objects.filter(
        intake__facility_id__in=facility_ids, status=SourceRowStatus.VERIFIED
    ).select_related("intake")
    if date_from:
        qs = qs.filter(service_date__gte=date_from)
    if date_to:
        qs = qs.filter(service_date__lte=date_to)

    by_fac = defaultdict(list)
    for r in qs:
        by_fac[str(r.intake.facility_id)].append(r)

    open_flags_by = defaultdict(int)
    for row in TemplateFlag.objects.filter(intake__facility_id__in=facility_ids, status=TemplateFlag.Status.OPEN).values("intake__facility_id"):
        open_flags_by[str(row["intake__facility_id"])] += 1

    facs = {str(f.id): f for f in Facility.objects.filter(id__in=facility_ids).select_related("ward__local_government__state")}
    tmpl_cache = {}
    rows = []
    for fid, f in facs.items():
        card = _facility_rdqa(by_fac.get(fid, []), open_flags_by.get(fid, 0), tmpl_cache)
        if card["rows"] == 0:
            continue
        card.update({
            "facility_id": fid, "name": f.name,
            "region": f"{f.ward.local_government.state.name} · {f.ward.local_government.name}",
        })
        rows.append(card)
    rows.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0)))

    scored = [r["score"] for r in rows if r["score"] is not None]
    confs = [r["avg_extraction_confidence"] for r in rows if r["avg_extraction_confidence"] is not None]
    overall = {
        "facilities_assessed": len(rows),
        "mean_score": round(sum(scored) / len(scored)) if scored else None,
        "mean_confidence": round(sum(confs) / len(confs), 3) if confs else None,
        "total_open_flags": sum(open_flags_by.values()),
    }
    return {"facilities": rows, "overall": overall}


def rdqa_trend(facility_ids, date_from=None, date_to=None) -> dict:
    """Mean extraction confidence by month (publish date)."""
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"points": []}
    qs = SourceRow.objects.filter(
        intake__facility_id__in=facility_ids, status=SourceRowStatus.VERIFIED, intake__status=IntakeStatus.PUBLISHED
    ).select_related("intake")
    buckets = defaultdict(list)
    for r in qs:
        pub = r.intake.published_at
        if not pub:
            continue
        key = f"{pub.year}-{pub.month:02d}"
        buckets[key].extend(v for v in (r.extraction_confidence or {}).values() if isinstance(v, (int, float)))
    points = [
        {"x": k, "numerator": round(sum(v) / len(v) * 100) if v else 0, "denominator": 100,
         "rate": round(sum(v) / len(v), 4) if v else None}
        for k, v in sorted(buckets.items())
    ]
    return {"points": points}
