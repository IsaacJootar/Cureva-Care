"""Death reviews — MPDSR (expansion M2).

Maternal & Perinatal Death Surveillance and Response: on top of the deaths we
already detect, every death gets a structured review — cause, was it avoidable,
what contributed, and a follow-up action. Avoidability/cause are a human
judgement recorded by the reviewer; we store and summarise it, we never infer it.

Woman-level review data is for the Facility lead of that facility only.
Organisations receive the aggregates (how many reviewed, how many avoidable,
what keeps contributing, whether actions get done) — never the woman-level case.
"""
from datetime import date

from maternal_projection.models import BirthEvent

from .models import DeathReview
from .surveillance import _severe_types

# Standard MPDSR cause categories (maternal + perinatal).
CAUSES = [
    {"key": "haemorrhage", "label": "Bleeding (haemorrhage)"},
    {"key": "hypertension", "label": "High blood pressure (pre-eclampsia/eclampsia)"},
    {"key": "sepsis", "label": "Infection (sepsis)"},
    {"key": "obstructed", "label": "Obstructed / prolonged labour"},
    {"key": "abortion", "label": "Complications of abortion"},
    {"key": "indirect", "label": "Other illness (malaria, anaemia, HIV…)"},
    {"key": "prematurity", "label": "Prematurity / low birth weight (baby)"},
    {"key": "asphyxia", "label": "Birth asphyxia (baby)"},
    {"key": "congenital", "label": "Birth defect (baby)"},
    {"key": "other", "label": "Other"},
    {"key": "unknown", "label": "Unknown"},
]
CAUSE_LABEL = {c["key"]: c["label"] for c in CAUSES}

# Contributing factors — the WHO "three delays" plus facility-side gaps.
FACTORS = [
    {"key": "delay_seeking", "label": "Delay in deciding to seek care"},
    {"key": "delay_reaching", "label": "Delay reaching the facility (transport/distance)"},
    {"key": "delay_receiving", "label": "Delay getting care at the facility"},
    {"key": "no_blood", "label": "Blood not available"},
    {"key": "no_drugs", "label": "Drugs or supplies not available"},
    {"key": "no_staff", "label": "No skilled staff available"},
    {"key": "referral_failed", "label": "Referral broke down"},
    {"key": "late_anc", "label": "Little or no antenatal care"},
]
FACTOR_LABEL = {f["key"]: f["label"] for f in FACTORS}

AVOIDABLE_LABEL = dict(DeathReview.Avoidable.choices)
ACTION_STATUS_LABEL = dict(DeathReview.ActionStatus.choices)


def catalogue() -> dict:
    return {
        "causes": CAUSES,
        "factors": FACTORS,
        "avoidable_options": [{"key": k, "label": v} for k, v in DeathReview.Avoidable.choices],
        "action_status_options": [{"key": k, "label": v} for k, v in DeathReview.ActionStatus.choices],
    }


def _death_births(facility_ids, date_from, date_to):
    qs = BirthEvent.objects.filter(facility_id__in=facility_ids)
    if date_from:
        qs = qs.filter(delivery_date__gte=date_from)
    if date_to:
        qs = qs.filter(delivery_date__lte=date_to)
    return [b for b in qs.select_related("woman") if _severe_types(b)]


def review_queue(facility_ids, date_from=None, date_to=None) -> dict:
    """Woman-level: each death with its review state. Facility-lead only."""
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"deaths": [], "catalogue": catalogue()}
    deaths = _death_births(facility_ids, date_from, date_to)
    reviews = {r.birth_event_id: r for r in DeathReview.objects.filter(birth_event_id__in=[b.id for b in deaths])}
    rows = []
    for b in deaths:
        r = reviews.get(b.id)
        reviewed = bool(r and (r.cause or r.avoidable != DeathReview.Avoidable.UNKNOWN or r.factors or r.action))
        rows.append({
            "birth_event_id": str(b.id),
            "episode_id": str(b.episode_id) if b.episode_id else None,
            "woman": {"internal_id": b.woman.internal_id, "name": b.woman.name} if b.woman_id else None,
            "outcomes": _severe_types(b),
            "delivery_date": b.delivery_date,
            "reviewed": reviewed,
            "review": _review_dict(r) if r else None,
        })
    rows.sort(key=lambda x: (x["reviewed"], x["delivery_date"] or date.min), reverse=False)
    return {"deaths": rows, "catalogue": catalogue()}


def _review_dict(r: DeathReview) -> dict:
    return {
        "cause": r.cause, "avoidable": r.avoidable, "factors": r.factors or [],
        "notes": r.notes, "action": r.action, "action_owner": r.action_owner,
        "action_status": r.action_status,
        "reviewed_at": r.reviewed_at,
    }


def mpdsr_summary(facility_ids, date_from=None, date_to=None) -> dict:
    """Aggregates only — safe for organisations."""
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"total_deaths": 0, "reviewed": 0, "awaiting": 0, "avoidable": [], "factors": [], "actions": []}
    deaths = _death_births(facility_ids, date_from, date_to)
    total = len(deaths)
    reviews = list(DeathReview.objects.filter(birth_event_id__in=[b.id for b in deaths]))
    reviewed_map = {
        r.birth_event_id: r for r in reviews
        if r.cause or r.avoidable != DeathReview.Avoidable.UNKNOWN or r.factors or r.action
    }
    reviewed = len(reviewed_map)

    # Avoidability breakdown (over reviewed deaths).
    av_counts = {k: 0 for k, _ in DeathReview.Avoidable.choices}
    factor_counts = {f["key"]: 0 for f in FACTORS}
    action_counts = {k: 0 for k, _ in DeathReview.ActionStatus.choices}
    actions_total = 0
    for r in reviewed_map.values():
        av_counts[r.avoidable] = av_counts.get(r.avoidable, 0) + 1
        for fk in (r.factors or []):
            if fk in factor_counts:
                factor_counts[fk] += 1
        if (r.action or "").strip():
            actions_total += 1
            action_counts[r.action_status] = action_counts.get(r.action_status, 0) + 1

    avoidable = [{"key": k, "label": AVOIDABLE_LABEL[k], "count": av_counts[k]} for k, _ in DeathReview.Avoidable.choices]
    factors = sorted(
        [{"key": k, "label": FACTOR_LABEL[k], "count": v} for k, v in factor_counts.items() if v > 0],
        key=lambda x: -x["count"],
    )
    actions = [{"key": k, "label": ACTION_STATUS_LABEL[k], "count": action_counts[k]} for k, _ in DeathReview.ActionStatus.choices]

    return {
        "total_deaths": total,
        "reviewed": reviewed,
        "awaiting": total - reviewed,
        "avoidable": avoidable,
        "factors": factors,
        "actions": actions,
        "actions_total": actions_total,
    }
