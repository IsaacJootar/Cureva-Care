"""Risk stratification + early-warning alerts (WS5)."""
import datetime

import pytest

from identity_access.models import AccessLevel, Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import ANCContact, PregnancyEpisode, Woman
from intelligence.risk import risk_pyramid, risk_registry
from intelligence.alerts import evaluate_alerts

D = datetime.date


@pytest.fixture
def facility(db):
    s = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=s, name="Nassarawa")
    w = Ward.objects.create(local_government=lga, name="Gama")
    return Facility.objects.create(ward=w, name="Gama PHC")


@pytest.fixture
def officer(db):
    return User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)


def _anc(facility, officer, name, data, svc=D(2026, 2, 1)):
    woman = Woman.objects.create(facility=facility, name=name, stable_identifier=f"S{Woman.objects.count()}")
    ep = PregnancyEpisode.objects.create(woman=woman, facility=facility, booking_date=D(2026, 1, 5))
    intake = Intake.objects.create(
        facility=facility, submitted_by=officer, register_family="ANC", source_hash=f"h{Intake.objects.count()}",
        batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 12, 31),
    )
    row = SourceRow.objects.create(intake=intake, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})
    ANCContact.objects.create(episode=ep, woman=woman, facility=facility, source_row=row, data=data, service_date=svc)
    return ep


@pytest.mark.django_db
def test_risk_tiers(facility, officer):
    _anc(facility, officer, "High", {"blood_pressure": "160/100"})       # High (raised BP)
    _anc(facility, officer, "Mod", {"parity": 6})                        # Moderate (grand multipara)
    _anc(facility, officer, "None", {"blood_pressure": "110/70"})        # None recorded
    pyr = risk_pyramid([facility.id])
    assert pyr["tiers"]["High"] == 1
    assert pyr["tiers"]["Moderate"] == 1
    assert pyr["tiers"]["None recorded"] == 1


@pytest.mark.django_db
def test_registry_lists_markers_and_hides_names_when_deidentified(facility, officer):
    _anc(facility, officer, "Amina", {"haemoglobin": "6.5"})  # severe anaemia → High
    reg = risk_registry([facility.id], AccessLevel.IDENTIFIABLE)
    assert reg["count"] == 1
    assert reg["rows"][0]["tier"] == "High"
    assert any("Severe anaemia" in m for m in reg["rows"][0]["markers"])
    assert reg["rows"][0]["woman"]["name"] == "Amina"
    deid = risk_registry([facility.id], AccessLevel.DE_IDENTIFIED)
    assert deid["rows"][0]["woman"] is None


@pytest.mark.django_db
def test_alerts_high_risk_overdue_fires(facility, officer):
    # High-risk pregnancy whose only ANC contact is long ago (overdue).
    _anc(facility, officer, "Overdue", {"blood_pressure": "170/110"}, svc=D(2026, 1, 1))
    alerts = evaluate_alerts([facility.id])
    kinds = {a["kind"] for a in alerts}
    assert "high_risk_overdue" in kinds
    # High-severity alerts sort first.
    assert alerts[0]["severity"] == "high"
