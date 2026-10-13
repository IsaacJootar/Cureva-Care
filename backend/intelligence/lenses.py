"""The 11 intelligence lenses (cureva-docs/06-metrics-and-reporting.md).

Every lens is built strictly from ANC/Delivery/PNC fields this package defines,
joined only through identity linkage and the facility hierarchy — no source
outside the three registers. Each returns counts WITH denominators (rule #5);
missing fields are never inferred (rule #6). A cross-register lens populates
only for linked episodes.
"""
from maternal_projection.models import ANCContact, BirthEvent, PNCContact, PregnancyEpisode, Referral
from register_intake.models import SourceRow, TemplateFlag


def _r(num, den):
    return {"numerator": num, "denominator": den, "rate": round(num / den, 4) if den else None}


def _f(qs, facility_ids):
    return qs.filter(facility_id__in=facility_ids)


def compute_lenses(facility_ids) -> dict:
    facility_ids = list(facility_ids or [])
    if not facility_ids:
        return {}

    anc = list(_f(ANCContact.objects, facility_ids).select_related("woman"))
    births = list(_f(BirthEvent.objects, facility_ids))
    pnc = list(_f(PNCContact.objects, facility_ids))
    refs = list(_f(Referral.objects, facility_ids))

    def anc_has(c, key):
        return (c.data or {}).get(key) not in (None, "")

    # 1. Perinatal & maternal surveillance (MPDSR-style): traceable severe cases.
    severe_cases = [
        {
            "woman": b.woman.internal_id,
            "outcome": "stillbirth" if b.still_birth else (b.maternal_outcome or b.baby_outcome),
            "delivery_date": b.delivery_date,
        }
        for b in births
        if b.still_birth or (b.maternal_outcome or "").lower() == "died" or (b.baby_outcome or "").lower() in ("stillbirth", "early neonatal death")
    ]
    lens1 = {"severe_case_count": len(severe_cases), "cases": severe_cases[:50]}

    # 2. High-risk pregnancy registry.
    def is_high_risk(c):
        d = c.data or {}
        hb = d.get("haemoglobin")
        geno = (d.get("genotype") or "").upper()
        try:
            anaemic = hb is not None and float(hb) < 11
        except (TypeError, ValueError):
            anaemic = False
        bp = str(d.get("blood_pressure") or "")
        import re
        m = re.match(r"\s*(\d+)\s*/\s*(\d+)", bp)
        raised_bp = bool(m) and (int(m.group(1)) >= 140 or int(m.group(2)) >= 90)
        return anaemic or raised_bp or geno in ("SS", "SC") or str(d.get("hiv_result") or "").lower() in ("positive", "reactive", "pos")
    high_risk = [c for c in anc if is_high_risk(c)]
    lens2 = {"high_risk_contacts": _r(len(high_risk), len(anc))}

    # 3. HIV/syphilis testing coverage & retention.
    hiv_tested = sum(1 for c in anc if anc_has(c, "hiv_result"))
    syph_tested = sum(1 for c in anc if anc_has(c, "syphilis_result"))
    lens3 = {
        "hiv_testing_coverage": _r(hiv_tested, len(anc)),
        "syphilis_testing_coverage": _r(syph_tested, len(anc)),
    }

    # 4. Postnatal coverage, timeliness & FP.
    early_pnc = sum(1 for p in pnc if (p.days_postpartum is not None and p.days_postpartum <= 2))
    fp = sum(1 for p in pnc if (p.data or {}).get("family_planning") not in (None, ""))
    lens4 = {
        "early_pnc_within_48h": _r(early_pnc, len(pnc)),
        "family_planning_documented": _r(fp, len(pnc)),
    }

    # 5. Referral rate & closure.
    closed = sum(1 for r in refs if r.status == Referral.Status.CLOSED)
    lens5 = {"referral_closure": _r(closed, len(refs))}

    # 6. Danger-sign detection-to-action.
    danger = [p for p in pnc if str((p.data or {}).get("danger_signs") or "").strip().lower() not in ("", "none", "nil", "no")]
    acted = sum(1 for p in danger if (p.referral_status or (p.visit_outcome or "").lower() in ("referred", "admitted")))
    lens6 = {"danger_sign_action": _r(acted, len(danger))}

    # 7. Facility delivery capability & outcome ratios.
    cs = sum(1 for b in births if (b.mode_of_delivery or "").upper() == "CS")
    skilled = sum(1 for b in births if (b.attendant_category or "") in ("Doctor", "Midwife", "Nurse"))
    deaths = sum(1 for b in births if (b.maternal_outcome or "").lower() == "died")
    lens7 = {
        "caesarean_rate": _r(cs, len(births)),
        "skilled_birth_attendance": _r(skilled, len(births)),
        "institutional_maternal_deaths": deaths,
        "total_deliveries": len(births),
    }

    # 8. Newborn birth-weight & early feeding.
    lbw = sum(1 for b in births if b.birth_weight_kg is not None and float(b.birth_weight_kg) < 2.5)
    weighed = sum(1 for b in births if b.birth_weight_kg is not None)
    exclusive = sum(1 for p in pnc if (p.feeding_status or "").lower().startswith("exclusive"))
    lens8 = {
        "low_birth_weight": _r(lbw, weighed),
        "exclusive_breastfeeding": _r(exclusive, len(pnc)),
    }

    # 9. Preventive intervention coverage.
    def covered(key):
        return _r(sum(1 for c in anc if (c.data or {}).get(key) is True), len(anc))
    lens9 = {
        "iron_folate": covered("iron_folate_given"),
        "tetanus": covered("tetanus_given"),
        "iptp": covered("iptp_given"),
    }

    # 10. Geographic equity — per-facility verified record counts (slice).
    from collections import Counter
    by_fac = Counter()
    for c in anc:
        by_fac[str(c.facility_id)] += 1
    for b in births:
        by_fac[str(b.facility_id)] += 1
    for p in pnc:
        by_fac[str(p.facility_id)] += 1
    lens10 = {"records_by_facility": dict(by_fac)}

    # 11. Data-quality / register-keeping signal.
    verified_rows = SourceRow.objects.filter(intake__facility_id__in=facility_ids, status="verified")
    confidences = []
    for row in verified_rows.only("extraction_confidence"):
        confidences.extend(v for v in (row.extraction_confidence or {}).values() if isinstance(v, (int, float)))
    avg_conf = round(sum(confidences) / len(confidences), 3) if confidences else None
    open_flags = TemplateFlag.objects.filter(intake__facility_id__in=facility_ids, status=TemplateFlag.Status.OPEN).count()
    lens11 = {"avg_extraction_confidence": avg_conf, "open_template_flags": open_flags}

    return {
        "perinatal_surveillance": lens1,
        "high_risk_registry": lens2,
        "hiv_syphilis_coverage": lens3,
        "postnatal_coverage": lens4,
        "referral_closure": lens5,
        "danger_sign_action": lens6,
        "delivery_capability": lens7,
        "newborn_weight_feeding": lens8,
        "preventive_coverage": lens9,
        "geographic_equity": lens10,
        "data_quality": lens11,
    }
