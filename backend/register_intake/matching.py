"""Field matching and the register-family cross-check.

These are the algorithms from cureva-docs/03-templates-and-intake.md. Field
matching ("which canonical field is this label?") is separate from extraction
confidence ("how sure is the model it read the value right?").

Matching is forgiving of how a real register prints a header: punctuation,
parentheses, slashes and word order are ignored (so "Hb (g/dl)" matches the
"Hb g/dl" alias and "Card/Folder No" matches "Card No"). To stay safe, the
word-subset fallback only uses aliases of two or more words — a single-letter
alias like "G" (Gravida) or "P" (Parity) can still only match exactly, so it
never gets pulled in by an unrelated column that merely contains that letter.
"""
import re

_SPLIT = re.compile(r"[^a-z0-9]+")


def _norm(text: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace: 'Hb (g/dl)' -> 'hb g dl'."""
    return " ".join(t for t in _SPLIT.split(text.lower()) if t)

# Signature fields: present on one register family, not the others. Shared
# fields (card_number, referral_status) carry no discriminating power and are
# excluded (cureva-docs/03 "Register-family cross-check").
REGISTER_SIGNATURE_FIELDS = {
    "ANC": {"lmp", "edd", "gravida", "parity", "gestational_age_weeks"},
    "Delivery": {"mode_of_delivery", "delivery_place", "attendant_category", "still_birth", "birth_weight_kg"},
    "PNC": {"days_postpartum", "subject", "maternal_assessment", "newborn_assessment", "feeding_status", "danger_signs"},
}


def match_extracted_fields(template: dict, extracted_labels: dict) -> dict:
    """Resolve each extracted label against the template's aliases — like a CSV
    header lookup, but tolerant of the punctuation/word-order a real register
    prints (see module docstring)."""
    exact: dict[str, str] = {}
    multi: list[tuple[frozenset, str, int]] = []  # (word-set, canonical, n-words)
    for col in template["columns"]:
        for name in list(col["aliases"]) + [col["label"]]:
            norm = _norm(name)
            if not norm:
                continue
            exact.setdefault(norm, col["canonical_field"])
            words = frozenset(norm.split(" "))
            if len(words) >= 2:
                multi.append((words, col["canonical_field"], len(words)))
    multi.sort(key=lambda m: -m[2])  # most specific (most words) first

    matched: dict[str, object] = {}
    taken: set[str] = set()
    unmatched: list[str] = []
    deferred: list[tuple[str, object, frozenset]] = []

    # Pass 1 — exact normalised match wins outright.
    for label, value in extracted_labels.items():
        norm = _norm(label)
        canonical = exact.get(norm)
        if canonical is not None:
            matched[canonical] = value
            taken.add(canonical)
        else:
            deferred.append((label, value, frozenset(norm.split(" ")) if norm else frozenset()))

    # Pass 2 — a multi-word alias whose words are all present in the label.
    for label, value, label_words in deferred:
        canonical = next(
            (c for words, c, _ in multi if c not in taken and words <= label_words),
            None,
        )
        if canonical is not None:
            matched[canonical] = value
            taken.add(canonical)
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
