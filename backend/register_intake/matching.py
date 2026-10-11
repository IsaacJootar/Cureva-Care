"""Field matching and the register-family cross-check.

These are the exact algorithms from cureva-docs/03-templates-and-intake.md.
Field matching ("which canonical field is this label?") is separate from
extraction confidence ("how sure is the model it read the value right?").
"""

# Signature fields: present on one register family, not the others. Shared
# fields (card_number, referral_status) carry no discriminating power and are
# excluded (cureva-docs/03 "Register-family cross-check").
REGISTER_SIGNATURE_FIELDS = {
    "ANC": {"lmp", "edd", "gravida", "parity", "gestational_age_weeks"},
    "Delivery": {"mode_of_delivery", "delivery_place", "attendant_category", "still_birth", "birth_weight_kg"},
    "PNC": {"days_postpartum", "subject", "maternal_assessment", "newborn_assessment", "feeding_status", "danger_signs"},
}


def match_extracted_fields(template: dict, extracted_labels: dict) -> dict:
    """Resolve each extracted label against the template's aliases, exactly like
    a CSV header lookup — but against text the model read from the image."""
    alias_lookup = {}
    for col in template["columns"]:
        for alias in col["aliases"]:
            alias_lookup[alias.strip().lower()] = col["canonical_field"]
        # The canonical label itself is also matchable.
        alias_lookup[col["label"].strip().lower()] = col["canonical_field"]

    matched, unmatched = {}, []
    for label, value in extracted_labels.items():
        key = label.strip().lower()
        if key in alias_lookup:
            matched[alias_lookup[key]] = value
        else:
            unmatched.append(label)

    return {"matched": matched, "unmatched": unmatched}


def detect_register_family(extracted_labels: dict, family_templates: dict) -> dict:
    """Return each family's count of matched signature fields.

    family_templates: {'ANC': <template>, 'Delivery': <template>, 'PNC': <template>}
    — the shared/default template per family is enough to tell the families apart.
    """
    scores = {}
    for family, template in family_templates.items():
        result = match_extracted_fields(template, extracted_labels)
        matched_keys = set(result["matched"].keys())
        scores[family] = len(matched_keys & REGISTER_SIGNATURE_FIELDS[family])
    return scores


def check_register_mismatch(declared_family: str, scores: dict, min_signal: int):
    """Return a suspected family only when another family is distinctly a better
    fit than the declared one. Never re-files the intake on its own — a human
    resolves it (cureva-docs/03)."""
    best_family = max(scores, key=scores.get)
    if (
        best_family != declared_family
        and scores[best_family] >= min_signal
        and scores[best_family] > scores.get(declared_family, 0)
    ):
        return best_family
    return None
