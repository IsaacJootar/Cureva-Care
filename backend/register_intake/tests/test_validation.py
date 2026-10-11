"""Type/structure + plausibility validation (cureva-docs/03, 06)."""
from register_intake.default_templates import ANC_V1, DELIVERY_V1
from register_intake.validation import validate_and_normalize


def test_coerces_types():
    out = validate_and_normalize(
        ANC_V1,
        {"gravida": "G2", "weight_kg": "62.5", "iron_folate_given": "Yes", "lmp": "01/02/2026"},
    )
    n = out["normalized"]
    assert n["gravida"] == 2
    assert n["weight_kg"] == 62.5
    assert n["iron_folate_given"] is True
    assert n["lmp"] == "2026-02-01"  # dd/mm/yyyy parsed
    assert out["flags"] == {}


def test_implausible_blood_pressure_is_flagged_not_blocked():
    out = validate_and_normalize(ANC_V1, {"blood_pressure": "300/10"})
    assert "blood_pressure" in out["flags"]
    assert out["flags"]["blood_pressure"]["kind"] == "implausible"
    # Still normalized (published once verified) — not dropped.
    assert out["normalized"]["blood_pressure"] == "300/10"


def test_plausible_blood_pressure_passes():
    out = validate_and_normalize(ANC_V1, {"blood_pressure": "120/80"})
    assert out["flags"] == {}


def test_implausible_birth_weight_is_flagged():
    out = validate_and_normalize(DELIVERY_V1, {"birth_weight_kg": "8.0"})
    assert out["flags"]["birth_weight_kg"]["kind"] == "implausible"
    out_ok = validate_and_normalize(DELIVERY_V1, {"birth_weight_kg": "3.2"})
    assert out_ok["flags"] == {}


def test_blank_is_unknown_not_flagged():
    out = validate_and_normalize(ANC_V1, {"haemoglobin": "", "blood_pressure": None})
    assert out["normalized"]["haemoglobin"] is None
    assert out["normalized"]["blood_pressure"] is None
    assert out["flags"] == {}


def test_bad_enum_is_type_flagged():
    out = validate_and_normalize(DELIVERY_V1, {"mode_of_delivery": "Flying"})
    assert out["flags"]["mode_of_delivery"]["kind"] == "type_error"
