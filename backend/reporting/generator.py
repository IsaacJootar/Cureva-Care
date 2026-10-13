"""Healthcare-facing report generator (cureva-docs/06 "Healthcare-facing
report").

Deterministic metrics and charts are generated first. An OPTIONAL LLM pass may
turn already-computed AGGREGATE metrics into prose — it never sees a
row-level/identifiable value, and cannot invent causes, impact, or prevalence.
"""
from django.conf import settings

from intelligence.lenses import compute_lenses
from intelligence.metrics import maternal_summary


def _rate_pct(ratio):
    return f"{round(ratio['rate'] * 100)}% ({ratio['numerator']}/{ratio['denominator']})" if ratio and ratio["rate"] is not None else "no data"


def build_sections(facility_ids, date_from=None, date_to=None) -> dict:
    summary = maternal_summary(facility_ids, date_from, date_to)
    lenses = compute_lenses(facility_ids)
    m = summary["metrics"]
    op = summary["operational"]
    oc = summary["outcomes"]

    sections = {
        "reporting_coverage": {
            "facilities_in_scope": summary["scope"]["facility_count"],
            "verified_records": op["verified_records"],
            "limitations": "Figures reflect recorded register activity only, not population rates; missing fields are not inferred.",
        },
        "anc_access_continuity": {
            "booked_episodes": summary["care_journey"]["booked_episodes"],
            "early_booking": m["early_anc_booking"],
            "four_contact": m["four_contact_completion"],
            "eight_contact": m["eight_contact_completion"],
            "delivery_linkage": summary["care_journey"]["delivery_linkage"],
            "postnatal_linkage": summary["care_journey"]["postnatal_linkage"],
        },
        "screening_intervention_referral": {
            "screening_coverage": m["screening_coverage"],
            "intervention_coverage": m["intervention_coverage"],
            "preventive": lenses.get("preventive_coverage"),
            "referral_closure": m["referral_closure"],
        },
        "outcomes": {
            "live_births": oc["live_births"],
            "still_births": oc["still_births"],
            "maternal_deaths": oc["maternal_deaths"],
            "low_birth_weight": oc["low_birth_weight"],
            "delivery_capability": lenses.get("delivery_capability"),
        },
        "facility_variation_data_quality": {
            "geographic_equity": lenses.get("geographic_equity"),
            "data_quality": lenses.get("data_quality"),
        },
        "ranked_actions": _ranked_actions(summary, lenses),
    }
    return sections


def _ranked_actions(summary, lenses):
    actions = []
    m = summary["metrics"]
    if m["eight_contact_completion"]["rate"] is not None and m["eight_contact_completion"]["rate"] < 0.5:
        actions.append({"action": "Strengthen ANC retention toward the 8-contact schedule", "owner": "Facility lead", "rationale": f"8+ ANC contacts at {_rate_pct(m['eight_contact_completion'])}.", "measure": "8-contact completion rate"})
    if m["referral_closure"]["rate"] is not None and m["referral_closure"]["rate"] < 0.8:
        actions.append({"action": "Document outcomes for open referrals", "owner": "Facility lead", "rationale": f"Referral closure at {_rate_pct(m['referral_closure'])}.", "measure": "Referral closure rate"})
    dq = lenses.get("data_quality", {})
    if dq.get("open_template_flags"):
        actions.append({"action": "Resolve open template flags to improve extraction accuracy", "owner": "Systems admin", "rationale": f"{dq['open_template_flags']} open template flag(s).", "measure": "Open template flags"})
    # Pad to three with generic continuity actions.
    while len(actions) < 3:
        actions.append({"action": "Maintain postnatal follow-up coverage", "owner": "Facility lead", "rationale": "Sustain delivery→PNC linkage.", "measure": "Postnatal linkage rate"})
    return actions[:3]


def generate_narrative(sections) -> str | None:
    """Optional aggregate-only prose. Returns None if no LLM key configured.
    Only non-identifiable aggregate metrics are sent — never any case-level or
    woman-level data (the geographic_equity/data_quality facility ids are opaque
    UUIDs, not PHI)."""
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        import json

        payload = json.dumps({
            "reporting_coverage": sections["reporting_coverage"],
            "anc_access_continuity": sections["anc_access_continuity"],
            "screening_intervention_referral": sections["screening_intervention_referral"],
            "outcomes": sections["outcomes"],
        }, default=str)
        resp = client.chat.completions.create(
            model=getattr(settings, "OPENAI_VISION_MODEL", "gpt-4o"),
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": (
                    "You are writing the executive interpretation of a maternal-health facility "
                    "report. Using ONLY these already-computed aggregate metrics, write 2 short "
                    "paragraphs describing the most material patterns and the single most important "
                    "change to act on. Do NOT invent causes, impact, prevalence, or any number not "
                    "present. State clearly that figures are recorded activity, not population rates.\n\n"
                    f"Metrics: {payload}"
                ),
            }],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return None
