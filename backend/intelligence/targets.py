"""Goals & Targets engine (expansion M7).

Tracks progress against configurable program goals (SDG 3.1 / national coverage
targets). Each goal is keyed to a computable indicator and compared to an
admin-set target percentage; the scorecard says on-track / off-track. All
current values are re-aggregations of the three registers — same source as every
other view — so a goal never depends on new data capture.
"""
from .benchmarking import _accumulate, _metric_value
from .continuum import care_funnel
from .models import ProgramTarget

# Indicators a goal can be set against. Each resolves to a 0–1 rate for the
# caller's scope. All computable from existing engines (no denominators needed),
# so the scorecard always works. `higher_is_better` is True for every coverage
# goal here.
TARGET_CATALOGUE = {
    "anc4_of_registered": {
        "label": "Reached 4+ check-ups",
        "help": "Of women who registered a pregnancy, the share who had at least four check-ups.",
    },
    "early_booking": {
        "label": "Registered in the first 3 months",
        "help": "Share of pregnancies registered early (first trimester).",
        "metric": "early_anc_booking",
    },
    "screening": {
        "label": "Tested (HIV, syphilis, anaemia)",
        "help": "Share of check-ups with a recorded screening test.",
        "metric": "screening_coverage",
    },
    "interventions": {
        "label": "Got preventives (iron, tetanus, malaria)",
        "help": "Share of check-ups with a recorded preventive treatment.",
        "metric": "intervention_coverage",
    },
    "postnatal": {
        "label": "Came back after birth",
        "help": "Share of births with a recorded postnatal visit.",
        "metric": "postnatal_linkage",
    },
}

# WHO/SDG-aligned starting defaults (percentages), seeded and editable.
DEFAULT_TARGETS = [
    {"key": "anc4_of_registered", "target_pct": 80, "order": 1},
    {"key": "early_booking", "target_pct": 60, "order": 2},
    {"key": "screening", "target_pct": 90, "order": 3},
    {"key": "interventions", "target_pct": 90, "order": 4},
    {"key": "postnatal", "target_pct": 70, "order": 5},
]


def _current_rate(key, scope_total, funnel):
    """Return (rate, numerator, denominator) for an indicator over the scope."""
    if key == "anc4_of_registered":
        steps = {s["label"]: s for s in funnel["steps"]}
        booked = funnel["total"]
        anc4 = steps.get("Had 4+ check-ups", {}).get("value", 0)
        return (round(anc4 / booked, 4) if booked else None, anc4, booked or None)
    if scope_total is None:
        return (None, 0, None)
    _, value, num, den = _metric_value(scope_total, TARGET_CATALOGUE[key]["metric"])
    return (value, num, den)


def target_progress(facility_ids, date_from=None, date_to=None) -> dict:
    facility_ids = list(facility_ids or [])
    targets = list(ProgramTarget.objects.filter(is_active=True))
    if not facility_ids or not targets:
        return {"goals": []}

    # Shared aggregates, computed once: a single summed accumulator over the
    # scope (for benchmarking rate metrics) + the care funnel.
    acc = _accumulate(facility_ids, date_from, date_to)
    scope_total = None
    for a in acc.values():
        if scope_total is None:
            scope_total = dict(a)
        else:
            for k, v in a.items():
                scope_total[k] += v
    funnel = care_funnel(facility_ids, date_from, date_to)

    goals = []
    for t in targets:
        if t.key not in TARGET_CATALOGUE:
            continue
        spec = TARGET_CATALOGUE[t.key]
        rate, num, den = _current_rate(t.key, scope_total, funnel)
        current_pct = round(rate * 100, 1) if rate is not None else None
        on_track = None if current_pct is None else current_pct >= t.target_pct
        goals.append({
            "key": t.key,
            "label": spec["label"],
            "help": spec["help"],
            "target_pct": t.target_pct,
            "current_pct": current_pct,
            "numerator": num,
            "denominator": den,
            "on_track": on_track,
        })
    return {"goals": goals}
