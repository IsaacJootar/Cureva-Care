"""Name normalisation and fuzzy similarity for identity matching.

Lives in one module with its own unit tests because it will need tuning on real
pilot data (IDENTITY_MATCHING_UPDATE.md Section B). Normalisation lowercases,
strips punctuation and honorifics, and ignores word order; similarity uses
Jaro-Winkler (no external dependency), which tolerates common spelling variants
(Fatima/Fatimah, Aisha/Ayesha).
"""
import re

# Honorifics / titles seen on Nigerian maternal registers — stripped before
# comparing, so "Mrs Fatima" and "Fatima" match.
HONORIFICS = {
    "mrs", "mr", "miss", "ms", "madam", "mma",
    "hajiya", "hajia", "alhaja", "alhaji", "mallam", "malam",
    "dr", "prof", "chief", "pastor", "rev", "mallama",
}

_PUNCT = re.compile(r"[^\w\s]")


def normalize_tokens(name: str) -> list[str]:
    if not name:
        return []
    s = _PUNCT.sub(" ", str(name).lower())
    tokens = [t for t in s.split() if t and t not in HONORIFICS]
    return tokens


def normalized_name(name: str) -> str:
    """Honorific-free, punctuation-free, word-order-independent form."""
    return " ".join(sorted(normalize_tokens(name)))


def jaro(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    len1, len2 = len(s1), len(s2)
    match_distance = max(len1, len2) // 2 - 1
    if match_distance < 0:
        match_distance = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = s2_matches[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0

    transpositions = 0
    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    transpositions //= 2

    return (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3.0


def jaro_winkler(s1: str, s2: str, p: float = 0.1) -> float:
    j = jaro(s1, s2)
    # Common-prefix bonus (up to 4 chars).
    prefix = 0
    for a, b in zip(s1, s2):
        if a == b:
            prefix += 1
        else:
            break
        if prefix == 4:
            break
    return j + prefix * p * (1 - j)


def name_similarity(a: str, b: str) -> float:
    """0-1 similarity between two names, honorific- and word-order-insensitive."""
    na, nb = normalized_name(a), normalized_name(b)
    if not na or not nb:
        return 0.0
    return round(jaro_winkler(na, nb), 3)
