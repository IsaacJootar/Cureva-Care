"""Early-warning alerts (WS5).

Proactive signals beyond the stale-facility alert: low coverage, a growing
referral backlog, a severe-outcome cluster, and high-risk pregnancies overdue for
follow-up. Every alert is explainable — it names the rule, the recorded figures,
and the configurable threshold it crossed (all thresholds live in
platform_settings, never hard-coded). Alerts are scope/facility-level signals, so
they carry no woman-level identifiers; case-level follow-up stays in the
Facility-lead worklist.
"""
from datetime import timedelta

from django.utils import timezone

from identity_access.services import get_setting
from identity_access.settings_registry import (
    COVERAGE_ALERT_FLOOR,
    HIGH_RISK_CONTACT_GAP_DAYS,
    REFERRAL_BACKLOG_DAYS,
    SEVERE_CLUSTER_RATE,
)
from maternal_projection.models import Referral

from .benchmarking import SMALL_SAMPLE, _accumulate
from .risk import high_risk_overdue
from .surveillance import facility_clusters

SEV_ORDER = {"high": 0, "medium": 1, "low": 2}


def evaluate_alerts(facility_ids) -> list[dict]:
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return []
    alerts = []

    floor = float(get_setting(COVERAGE_ALERT_FLOOR))
    backlog_days = int(get_setting(REFERRAL_BACKLOG_DAYS))
    cluster_rate = float(get_setting(SEVERE_CLUSTER_RATE))
    gap_days = int(get_setting(HIGH_RISK_CONTACT_GAP_DAYS))

    from identity_access.models import Facility
    fac_names = {str(f.id): f.name for f in Facility.objects.filter(id__in=facility_ids)}

    # 1. Low coverage per facility (only where there's enough data to judge).
    acc = _accumulate(facility_ids, None, None)
    for fid, a in acc.items():
        for num, den, label in (
            (a["screen_num"], a["screen_den"], "Screening coverage"),
            (a["interv_num"], a["interv_den"], "Intervention coverage"),
        ):
            if den >= SMALL_SAMPLE and (num / den) < floor:
                alerts.append({
                    "kind": "low_coverage", "severity": "medium",
                    "title": f"Low {label.lower()} at {fac_names.get(fid, 'a facility')}",
                    "detail": f"{label} is {round(num / den * 100)}% ({num}/{den}), below the {round(floor * 100)}% floor.",
                    "facility_id": fid, "threshold": floor,
                })

    # 2. Referral backlog (open referrals older than the window).
    cutoff = (timezone.now() - timedelta(days=backlog_days)).date()
    backlog = Referral.objects.filter(facility_id__in=facility_ids, status=Referral.Status.OPEN, date__lte=cutoff).count()
    if backlog > 0:
        alerts.append({
            "kind": "referral_backlog", "severity": "medium",
            "title": f"{backlog} referral(s) open beyond {backlog_days} days",
            "detail": f"{backlog} referral(s) have had no documented outcome for more than {backlog_days} days.",
            "facility_id": None, "threshold": backlog_days,
        })

    # 3. Severe-outcome clusters.
    for f in facility_clusters(facility_ids)["facilities"]:
        if f["rate"] is not None and f["deliveries"] >= SMALL_SAMPLE and f["rate"] >= cluster_rate:
            alerts.append({
                "kind": "severe_cluster", "severity": "high",
                "title": f"Elevated severe-outcome rate at {f['name']}",
                "detail": f"{f['severe']} severe outcome(s) in {f['deliveries']} deliveries ({round(f['rate'] * 100)}%), at/above the {round(cluster_rate * 100)}% threshold.",
                "facility_id": f["facility_id"], "threshold": cluster_rate,
            })

    # 4. High-risk pregnancies overdue for follow-up.
    overdue = high_risk_overdue(facility_ids, gap_days)
    if overdue > 0:
        alerts.append({
            "kind": "high_risk_overdue", "severity": "high",
            "title": f"{overdue} high-risk pregnancy(ies) overdue for follow-up",
            "detail": f"{overdue} high-risk pregnancy(ies) have no recorded ANC contact in over {gap_days} days. See the Needs-attention worklist for the women.",
            "facility_id": None, "threshold": gap_days,
        })

    alerts.sort(key=lambda a: SEV_ORDER.get(a["severity"], 3))
    return alerts
