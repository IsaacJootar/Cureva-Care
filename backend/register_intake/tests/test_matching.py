"""Field matching + register-family cross-check (cureva-docs/03)."""
from register_intake.default_templates import ANC_V1, DELIVERY_V1, PNC_V1
from register_intake.matching import (
    check_register_mismatch,
    detect_register_family,
    match_extracted_fields,
)

FAMILY_TEMPLATES = {"ANC": ANC_V1, "Delivery": DELIVERY_V1, "PNC": PNC_V1}


def test_match_resolves_aliases_and_collects_unmatched():
    extracted = {"LMP": "2026-01-01", "Grav": "2", "Para": "1", "Mystery Column": "x"}
    result = match_extracted_fields(ANC_V1, extracted)
    assert result["matched"]["lmp"] == "2026-01-01"
    assert result["matched"]["gravida"] == "2"
    assert result["matched"]["parity"] == "1"
    assert result["unmatched"] == ["Mystery Column"]


def test_detect_family_scores_anc_highest_for_anc_page():
    extracted = {"LMP": "x", "EDD": "y", "Gravida": "2", "Parity": "1", "GA Weeks": "12"}
    scores = detect_register_family(extracted, FAMILY_TEMPLATES)
    assert scores["ANC"] == 5
    assert scores["ANC"] > scores["Delivery"]
    assert scores["ANC"] > scores["PNC"]


def test_detect_family_scores_delivery_highest_for_delivery_page():
    extracted = {
        "Mode of Delivery": "SVD",
        "Place of Delivery": "Facility",
        "Birth Attendant": "Midwife",
        "Stillbirth": "No",
        "Birth Weight": "3.2",
    }
    scores = detect_register_family(extracted, FAMILY_TEMPLATES)
    assert scores["Delivery"] == 5
    assert scores["Delivery"] > scores["ANC"]


def test_check_mismatch_flags_delivery_page_declared_as_anc():
    # A Delivery page mistakenly submitted as ANC must be flagged.
    extracted = {
        "Mode of Delivery": "CS",
        "Place of Delivery": "Facility",
        "Birth Attendant": "Doctor",
        "Birth Weight": "3.0",
    }
    scores = detect_register_family(extracted, FAMILY_TEMPLATES)
    suspected = check_register_mismatch("ANC", scores, min_signal=2)
    assert suspected == "Delivery"


def test_check_mismatch_returns_none_when_declared_matches():
    extracted = {"LMP": "x", "EDD": "y", "Gravida": "2", "Parity": "1"}
    scores = detect_register_family(extracted, FAMILY_TEMPLATES)
    assert check_register_mismatch("ANC", scores, min_signal=2) is None


def test_shared_fields_do_not_discriminate():
    # card_number + referral_status appear on all three; they must not tip the
    # balance toward any family.
    extracted = {"Card No": "123", "Referral": "yes"}
    scores = detect_register_family(extracted, FAMILY_TEMPLATES)
    assert scores == {"ANC": 0, "Delivery": 0, "PNC": 0}
