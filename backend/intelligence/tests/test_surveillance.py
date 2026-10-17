"""MPDSR severe-outcome surveillance (WS4)."""
import datetime

import pytest

from identity_access.models import AccessLevel, Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import ANCContact, BirthEvent, PregnancyEpisode, Woman
from intelligence.surveillance import case_timeline, facility_clusters, severe_cases, severe_trend

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


def _row(facility, officer, fam):
    intake = Intake.objects.create(
        facility=facility, submitted_by=officer, register_family=fam, source_hash=f"h{Intake.objects.count()}",
        batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 12, 31),
    )
    return SourceRow.objects.create(intake=intake, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})


def _case(facility, officer, name, outcome):
    woman = Woman.objects.create(facility=facility, name=name, stable_identifier=f"S{Woman.objects.count()}")
    ep = PregnancyEpisode.objects.create(woman=woman, facility=facility, booking_date=D(2026, 1, 5))
    # Antenatal risk: raised BP recorded.
    ANCContact.objects.create(episode=ep, woman=woman, facility=facility, source_row=_row(facility, officer, "ANC"), data={"blood_pressure": "160/100"}, service_date=D(2026, 2, 1))
    kw = {}
    if outcome == "stillbirth":
        kw["still_birth"] = True
    elif outcome == "maternal_death":
        kw["maternal_outcome"] = "Died"
    BirthEvent.objects.create(episode=ep, woman=woman, facility=facility, source_row=_row(facility, officer, "Delivery"), data={}, delivery_date=D(2026, 6, 1), mode_of_delivery="SVD", **kw)
    return woman, ep


@pytest.mark.django_db
def test_severe_cases_carries_antenatal_risk(facility, officer):
    _case(facility, officer, "Amina", "stillbirth")
    # A normal delivery should NOT appear.
    woman = Woman.objects.create(facility=facility, name="Normal", stable_identifier="SN")
    ep = PregnancyEpisode.objects.create(woman=woman, facility=facility)
    BirthEvent.objects.create(episode=ep, woman=woman, facility=facility, source_row=_row(facility, officer, "Delivery"), data={}, delivery_date=D(2026, 6, 2), still_birth=False)

    out = severe_cases([facility.id], AccessLevel.IDENTIFIABLE)
    assert out["count"] == 1
    c = out["cases"][0]
    assert c["woman"]["name"] == "Amina"
    assert "Stillbirth" in c["outcomes"]
    assert "Raised BP" in c["antenatal_risk"]


@pytest.mark.django_db
def test_severe_cases_aggregate_tier_counts_only(facility, officer):
    _case(facility, officer, "Amina", "maternal_death")
    out = severe_cases([facility.id], AccessLevel.AGGREGATE)
    assert out["count"] == 1
    assert out["cases"] == []
    assert out["by_type"]["Maternal death"] == 1


@pytest.mark.django_db
def test_case_timeline_orders_events(facility, officer):
    _, ep = _case(facility, officer, "Amina", "stillbirth")
    tl = case_timeline(ep.id, [facility.id], AccessLevel.IDENTIFIABLE)
    kinds = [e["type"] for e in tl["events"]]
    assert kinds == ["ANC", "Delivery"]  # chronological


@pytest.mark.django_db
def test_trend_and_clusters(facility, officer):
    _case(facility, officer, "Amina", "stillbirth")
    _case(facility, officer, "Bisi", "maternal_death")
    trend = severe_trend([facility.id])
    assert trend["series"]["Stillbirth"][0]["value"] == 1
    clusters = facility_clusters([facility.id])
    assert clusters["facilities"][0]["severe"] == 2
    assert clusters["facilities"][0]["deliveries"] == 2
