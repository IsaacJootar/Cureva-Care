"""Risk / referral / follow-up rule engine (cureva-docs/06 "Risk and follow-up
rules").

Rules operate only on recorded values — a blank is unknown, never a clear
result (rule #6). Each rule is versioned with a clinical owner, effective date,
source guidance, and severity. Rules create operational follow-up prompts; they
never diagnose or prescribe. Worklist items are COMPUTED from the maternal
model (not stored); a WorklistAction overlay records follow-up without ever
touching the register data, and an item resurfaces while its rule still
evaluates true (cureva-docs/02 "Worklist actions").

The rule thresholds are standard WHO-aligned defaults, accepted as the program
baseline. They flag recorded values for operational follow-up — they are never a
diagnosis. A program may still version a local adaptation later.
"""
from datetime import date

from maternal_projection.models import ANCContact, BirthEvent, PNCContact, PregnancyEpisode, Referral

CLINICAL_OWNER_PENDING = "WHO-aligned program default"

# Rule metadata registry. Each rule's evaluator yields worklist items.
RULE_META = {
    "abnormal_bp": {
        "label": "Raised blood pressure recorded",
        "severity": "high",
        "version": 1,
        "effective_date": "2026-01-01",
        "clinical_owner": CLINICAL_OWNER_PENDING,
        "source_guidance": "ANC contact with systolic ≥140 or diastolic ≥90 mmHg.",
    },
    "anaemia": {
        "label": "Low blood level (anaemia) recorded",
        "severity": "medium",
        "version": 1,
        "effective_date": "2026-01-01",
        "clinical_owner": CLINICAL_OWNER_PENDING,
        "source_guidance": "ANC contact with haemoglobin below 11 g/dl.",
    },
    "danger_signs": {
        "label": "Danger signs after birth recorded",
        "severity": "high",
        "version": 1,
        "effective_date": "2026-01-01",
        "clinical_owner": CLINICAL_OWNER_PENDING,
        "source_guidance": "PNC contact with danger signs recorded and not resolved.",
    },
    "open_referral": {
        "label": "Referral with no recorded outcome",
        "severity": "medium",
        "version": 1,
        "effective_date": "2026-01-01",
        "clinical_owner": CLINICAL_OWNER_PENDING,
        "source_guidance": "A referral recorded as open (no documented closure).",
    },
    "missing_postnatal": {
        "label": "Gave birth, no after-birth check-up",
        "severity": "medium",
        "version": 1,
        "effective_date": "2026-01-01",
        "clinical_owner": CLINICAL_OWNER_PENDING,
        "source_guidance": "A delivered episode with no linked PNC contact.",
    },
}


def _bp_abnormal(value) -> bool:
    import re

    m = re.match(r"\s*(\d+)\s*/\s*(\d+)", str(value or ""))
    if not m:
        return False
    return int(m.group(1)) >= 140 or int(m.group(2)) >= 90


def _item(rule_key, subject_type, subject_id, woman, reason, trigger_date):
    meta = RULE_META[rule_key]
    days_open = (date.today() - trigger_date).days if trigger_date else None
    return {
        "item_id": f"{rule_key}:{subject_id}",
        "rule_key": rule_key,
        "label": meta["label"],
        "severity": meta["severity"],
        "clinical_owner": meta["clinical_owner"],
        "subject_type": subject_type,
        "subject_id": str(subject_id),
        "woman": {"internal_id": woman.internal_id, "name": woman.name} if woman else None,
        "reason": reason,
        "days_open": days_open,
    }


def evaluate_worklist(facility_ids) -> list[dict]:
    """Compute all currently-true worklist items for the given facilities."""
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return []
    items = []

    for c in ANCContact.objects.filter(facility_id__in=facility_ids).select_related("woman"):
        bp = (c.data or {}).get("blood_pressure")
        if _bp_abnormal(bp):
            items.append(_item("abnormal_bp", "anc_contact", c.id, c.woman, f"Blood pressure {bp} recorded.", c.service_date))
        hb = (c.data or {}).get("haemoglobin")
        try:
            if hb is not None and float(hb) < 11:
                items.append(_item("anaemia", "anc_contact", c.id, c.woman, f"Haemoglobin {hb} g/dl recorded.", c.service_date))
        except (TypeError, ValueError):
            pass

    for p in PNCContact.objects.filter(facility_id__in=facility_ids).select_related("woman"):
        ds = (p.data or {}).get("danger_signs")
        if ds and str(ds).strip().lower() not in ("", "none", "nil", "no"):
            items.append(_item("danger_signs", "pnc_contact", p.id, p.woman, f"Danger signs: {ds}.", p.visit_date))

    for r in Referral.objects.filter(facility_id__in=facility_ids, status=Referral.Status.OPEN).select_related("woman"):
        items.append(_item("open_referral", "referral", r.id, r.woman, r.reason or "Referral recorded as open.", r.date))

    # Delivered episodes with no PNC contact.
    delivered_eps = PregnancyEpisode.objects.filter(
        facility_id__in=facility_ids, status="delivered"
    ).select_related("woman")
    for ep in delivered_eps:
        if not PNCContact.objects.filter(episode=ep).exists():
            bd = BirthEvent.objects.filter(episode=ep).values_list("delivery_date", flat=True).first()
            items.append(_item("missing_postnatal", "pregnancy_episode", ep.id, ep.woman, "No postnatal contact recorded after delivery.", bd))

    # Highest severity first.
    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda i: (order.get(i["severity"], 3), -(i["days_open"] or 0)))
    return items
