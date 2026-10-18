"""Transparent, rule-based risk stratification (WS5).

A pregnancy's risk TIER is a plain, explainable function of the risk markers
RECORDED on its ANC contacts — never a black-box score, never a diagnosis, and
every tier shows exactly which recorded markers produced it. The marker
thresholds are conservative WHO-aligned defaults, accepted as the program
baseline; a tier is an operational prioritisation, never a diagnosis.

Tier:
  High          — at least one high-severity marker recorded.
  Moderate      — at least one moderate marker (and no high marker).
  None recorded — no risk markers recorded (NOT "low risk" clinically — absence
                  of a recorded marker is not evidence of safety; rule #6).
"""
import re
from datetime import date

from identity_access.models import AccessLevel
from maternal_projection.models import ANCContact, BirthEvent, PregnancyEpisode

RISK_RULESET_VERSION = 1
CLINICAL_OWNER = "WHO-aligned program default"


def _bp_high(value) -> bool:
    m = re.match(r"\s*(\d+)\s*/\s*(\d+)", str(value or ""))
    return bool(m) and (int(m.group(1)) >= 140 or int(m.group(2)) >= 90)


def _markers_for_episode(episode_id) -> tuple[str, list[str]]:
    """Return (tier, sorted recorded markers) for one episode's ANC contacts."""
    high, moderate = set(), set()
    for c in ANCContact.objects.filter(episode_id=episode_id).only("data"):
        d = c.data or {}
        if _bp_high(d.get("blood_pressure")):
            high.add("Raised BP (≥140/90)")
        hb = d.get("haemoglobin")
        try:
            if hb is not None:
                hbf = float(hb)
                if hbf < 7:
                    high.add("Severe anaemia (Hb <7)")
                elif hbf < 11:
                    moderate.add("Anaemia (Hb <11)")
        except (TypeError, ValueError):
            pass
        if (d.get("genotype") or "").upper() in ("SS", "SC"):
            high.add("Sickle-cell (SS/SC)")
        if str(d.get("hiv_result") or "").lower() in ("positive", "reactive", "pos"):
            high.add("HIV positive")
        if str(d.get("syphilis_result") or "").lower() in ("positive", "reactive", "pos"):
            high.add("Syphilis positive")
        if str(d.get("blood_group_rhesus") or "").strip().endswith("-"):
            moderate.add("Rhesus-negative blood")
        try:
            if d.get("parity") is not None and int(d["parity"]) >= 5:
                moderate.add("Many previous births (5+)")
        except (TypeError, ValueError):
            pass
    markers = sorted(high) + sorted(moderate)
    tier = "High" if high else ("Moderate" if moderate else "None recorded")
    return tier, markers


def _active_episodes(facility_ids):
    """Undelivered episodes — the current caseload to stratify."""
    delivered = set(BirthEvent.objects.filter(facility_id__in=facility_ids).values_list("episode_id", flat=True))
    eps = PregnancyEpisode.objects.filter(facility_id__in=facility_ids).select_related("woman")
    return [e for e in eps if e.id not in delivered]


def risk_pyramid(facility_ids) -> dict:
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"tiers": {"High": 0, "Moderate": 0, "None recorded": 0}, "total": 0}
    counts = {"High": 0, "Moderate": 0, "None recorded": 0}
    for e in _active_episodes(facility_ids):
        tier, _ = _markers_for_episode(e.id)
        counts[tier] += 1
    return {"tiers": counts, "total": sum(counts.values()), "ruleset_version": RISK_RULESET_VERSION, "clinical_owner": CLINICAL_OWNER}


def risk_registry(facility_ids, access_level, tier_filter=None, limit=500) -> dict:
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {"rows": [], "count": 0}
    rank = {"High": 0, "Moderate": 1, "None recorded": 2}
    rows = []
    for e in _active_episodes(facility_ids):
        tier, markers = _markers_for_episode(e.id)
        if tier == "None recorded":
            continue  # registry lists pregnancies with at least one recorded marker
        if tier_filter and tier != tier_filter:
            continue
        last_anc = ANCContact.objects.filter(episode_id=e.id).order_by("-service_date").values_list("service_date", flat=True).first()
        rows.append({
            "episode_id": str(e.id),
            "tier": tier,
            "markers": markers,
            "woman": None if access_level == AccessLevel.DE_IDENTIFIED else {"internal_id": e.woman.internal_id, "name": e.woman.name},
            "woman_internal_id": e.woman.internal_id,
            "booking_date": e.booking_date,
            "last_anc": last_anc,
            "days_since_anc": (date.today() - last_anc).days if last_anc else None,
        })
    count = len(rows)
    if access_level == AccessLevel.AGGREGATE:
        return {"rows": [], "count": count, "access_level": access_level}
    rows.sort(key=lambda r: (rank[r["tier"]], -(r["days_since_anc"] or 0)))
    return {"rows": rows[:limit], "count": count, "access_level": access_level,
            "ruleset_version": RISK_RULESET_VERSION, "clinical_owner": CLINICAL_OWNER}


def high_risk_overdue(facility_ids, gap_days) -> int:
    """Count of active HIGH-risk episodes with no ANC contact within gap_days."""
    facility_ids = list(facility_ids or [])
    n = 0
    for e in _active_episodes(facility_ids):
        tier, _ = _markers_for_episode(e.id)
        if tier != "High":
            continue
        last = ANCContact.objects.filter(episode_id=e.id).order_by("-service_date").values_list("service_date", flat=True).first()
        if last is None or (date.today() - last).days > gap_days:
            n += 1
    return n
