"""Name normalisation + fuzzy similarity (IDENTITY_MATCHING_UPDATE.md Section B)."""
from maternal_projection.name_matching import name_similarity, normalized_name


def test_strips_honorifics_and_ignores_word_order():
    assert normalized_name("Mrs Fatima Bello") == "bello fatima"
    assert normalized_name("Hajiya Bello Fatima") == "bello fatima"
    assert name_similarity("Mrs Fatima Bello", "Bello Fatima") == 1.0


def test_tolerates_common_spelling_variants():
    assert name_similarity("Fatima", "Fatimah") >= 0.9
    assert name_similarity("Aisha", "Ayesha") >= 0.8


def test_different_names_score_low():
    assert name_similarity("Amina Yusuf", "Grace Okafor") < 0.6


def test_blank_or_missing_scores_zero():
    assert name_similarity("", "Fatima") == 0.0
    assert name_similarity("Fatima", "") == 0.0


def test_identical_scores_one():
    assert name_similarity("Zainab Musa", "zainab   musa") == 1.0
