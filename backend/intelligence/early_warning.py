"""Early warning engine (expansion M3).

Moves selected signals from reactive to anticipatory: a watch list of facilities
whose numbers are heading the wrong way, so a programme can act BEFORE harm. Kept
deliberately simple and explainable (doc 12, principle 10) — plain trends over
recent months, never a black box. Every item shows the numbers behind it and is a
prompt to look, not a verdict.
"""
from collections import defaultdict

from identity_access.models import Facility
from maternal_projection.models import ANCContact, BirthEvent

from .surveillance import _severe_types

MIN_MONTHS = 3          # need at least this much history to judge a trend
MIN_ACTIVITY = 3        # ignore facilities too small for a trend to mean anything


def _mkey(d):
    return f"{d.year}-{d.month:02d}" if d else None


def early_warnings(facility_ids, months=6) -> dict:
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"watch": [], "window": []}

    anc_by = defaultdict(lambda: defaultdict(int))     # fid -> month -> ANC count
    births_by = defaultdict(lambda: defaultdict(int))  # fid -> month -> births
    severe_by = defaultdict(lambda: defaultdict(int))  # fid -> month -> severe outcomes

    for c in ANCContact.objects.filter(facility_id__in=facility_ids).only("facility_id", "service_date"):
        if c.service_date:
            anc_by[str(c.facility_id)][_mkey(c.service_date)] += 1
    for b in BirthEvent.objects.filter(facility_id__in=facility_ids).only("facility_id", "delivery_date", "still_birth", "maternal_outcome", "baby_outcome"):
        if b.delivery_date:
            fid, m = str(b.facility_id), _mkey(b.delivery_date)
            births_by[fid][m] += 1
            if _severe_types(b):
                severe_by[fid][m] += len(_severe_types(b))

    all_months = sorted(
        {m for d in anc_by.values() for m in d} | {m for d in births_by.values() for m in d}
    )
    if not all_months:
        return {"watch": [], "window": []}
    window = all_months[-months:]
    end = len(window) - 1

    facs = Facility.objects.filter(id__in=facility_ids).select_related("ward__local_government__state")
    watch = []
    for f in facs:
        fid = str(f.id)
        anc = [anc_by[fid].get(m, 0) for m in window]
        births = [births_by[fid].get(m, 0) for m in window]
        severe = [severe_by[fid].get(m, 0) for m in window]
        active = sum(1 for v in anc if v > 0) + sum(1 for v in births if v > 0)

        base = {"facility_id": fid, "name": f.name, "region": f.region_path}

        # --- Gone quiet: used to report, but nothing recently -----------------
        last_active = max([i for i, (a, b2) in enumerate(zip(anc, births)) if a or b2], default=-1)
        if last_active >= 0 and last_active <= end - 2 and any(anc[: last_active + 1]):
            gap = end - last_active
            watch.append({**base, "type": "gone_quiet", "severity": "high",
                          "headline": "Reporting may have stopped",
                          "detail": f"No new records for about {gap} month{'s' if gap != 1 else ''}, after reporting regularly. Check whether the facility is still submitting."})
            continue

        if active < MIN_MONTHS or len(window) < MIN_MONTHS:
            continue

        # --- Activity falling -------------------------------------------------
        prev, recent = anc[:-1], anc[-1]
        prev_avg = sum(prev) / len(prev) if prev else 0
        if prev_avg >= MIN_ACTIVITY and recent < prev_avg:
            drop = 1 - (recent / prev_avg)
            if drop >= 0.3:
                sev = "high" if drop >= 0.5 else "medium"
                watch.append({**base, "type": "activity_falling", "severity": sev,
                              "headline": "Pregnancy check-ups are falling",
                              "detail": f"About {round(prev_avg)} a month until recently, now {recent} — down {round(drop * 100)}%. On track to keep dropping unless something changes."})

        # --- Severe outcomes rising (possible cluster) ------------------------
        half = max(1, len(window) // 2)
        early_sev, early_bir = sum(severe[:-half]), sum(births[:-half])
        late_sev, late_bir = sum(severe[-half:]), sum(births[-half:])
        early_rate = (early_sev / early_bir) if early_bir else 0
        late_rate = (late_sev / late_bir) if late_bir else 0
        if late_sev >= 2 and late_rate > 0.05 and late_rate > early_rate * 1.5:
            watch.append({**base, "type": "severe_rising", "severity": "high",
                          "headline": "Deaths & stillbirths are climbing",
                          "detail": f"{late_sev} in {late_bir} recent births ({round(late_rate * 100)}%), up from {round(early_rate * 100)}% earlier. Watch for a cluster and review recent cases."})

    order = {"high": 0, "medium": 1, "low": 2}
    watch.sort(key=lambda w: order.get(w["severity"], 9))
    return {"watch": watch, "window": window}
