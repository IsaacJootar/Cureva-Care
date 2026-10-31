"""Referral pathways & outcomes engine (expansion M5).

Closes the loop on referrals: when a woman is sent to a bigger facility, did she
get there, and what happened? Referral breakdowns are where mothers die, and on
paper the outcome is usually invisible. Arrival/outcome capture is OPTIONAL, so a
referral with neither recorded is counted as "we don't know" — which is itself
the headline signal of a broken referral loop.
"""
from collections import Counter, defaultdict
from datetime import date

from identity_access.models import Facility
from maternal_projection.models import Referral


def _rate(num, den):
    return round(num / den, 4) if den else None


def referrals_summary(facility_ids, date_from=None, date_to=None) -> dict:
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"total": 0, "funnel": [], "unknown": 0, "by_facility": [], "destinations": [], "lost": []}

    qs = Referral.objects.filter(facility_id__in=facility_ids)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    refs = list(qs.select_related("woman"))
    total = len(refs)

    def has_outcome(r):
        return r.status == Referral.Status.CLOSED or bool((r.outcome or "").strip())

    arrived = sum(1 for r in refs if r.arrived is True)
    outcome_known = sum(1 for r in refs if has_outcome(r))
    # Loop never closed: no arrival recorded AND no outcome recorded.
    unknown = sum(1 for r in refs if r.arrived is None and not has_outcome(r))

    funnel = [
        {"label": "Referred to a bigger facility", "value": total},
        {"label": "Confirmed she arrived", "value": arrived},
        {"label": "Outcome recorded", "value": outcome_known},
    ]
    for i, step in enumerate(funnel):
        step["share"] = _rate(step["value"], total) if i > 0 else 1.0 if total else None

    # Per facility: share where the loop was closed (an outcome is known).
    by_fac = defaultdict(lambda: {"total": 0, "known": 0})
    for r in refs:
        a = by_fac[str(r.facility_id)]
        a["total"] += 1
        if has_outcome(r):
            a["known"] += 1
    facs = {str(f.id): f for f in Facility.objects.filter(id__in=facility_ids).select_related("ward__local_government__state")}
    by_facility = []
    for fid, a in by_fac.items():
        f = facs.get(fid)
        by_facility.append({
            "facility_id": fid, "name": f.name if f else "?", "region": f.region_path if f else "",
            "total": a["total"], "outcome_known": a["known"], "rate": _rate(a["known"], a["total"]),
        })
    by_facility.sort(key=lambda r: (r["rate"] is None, r["rate"] or 0))  # worst loop-closing first

    # Where women are sent.
    dest = Counter((r.destination or "Not recorded").strip() or "Not recorded" for r in refs)
    destinations = [{"name": k, "count": v} for k, v in dest.most_common(8)]

    # Referrals that went nowhere: open, no arrival/outcome, oldest first.
    lost = [
        {
            "woman_internal_id": r.woman.internal_id,
            "reason": (r.reason or "").strip() or None,
            "destination": (r.destination or "").strip() or None,
            "date": r.date,
            "days_open": (date.today() - r.date).days if r.date else None,
        }
        for r in refs
        if r.arrived is None and not has_outcome(r)
    ]
    lost.sort(key=lambda r: (r["days_open"] is None, -(r["days_open"] or 0)))

    return {
        "total": total,
        "arrived": arrived,
        "outcome_known": outcome_known,
        "unknown": unknown,
        "funnel": funnel,
        "by_facility": by_facility,
        "destinations": destinations,
        "lost": lost[:100],
    }
