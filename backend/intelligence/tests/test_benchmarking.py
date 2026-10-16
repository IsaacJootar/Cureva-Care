"""Benchmarking & equity engine (WS2)."""
import datetime

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import ANCContact, BirthEvent, PregnancyEpisode, Woman
from intelligence.benchmarking import equity_by_parity, facility_league, geo_rollup

D = datetime.date


@pytest.fixture
def geo(db):
    state = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=state, name="Nassarawa")
    w1 = Ward.objects.create(local_government=lga, name="Gama")
    w2 = Ward.objects.create(local_government=lga, name="Kundila")
    f1 = Facility.objects.create(ward=w1, name="Gama PHC")
    f2 = Facility.objects.create(ward=w2, name="Kundila PHC")
    officer = User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)
    return state, lga, f1, f2, officer


def _birth(facility, officer, n, parity=1):
    woman = Woman.objects.create(facility=facility, name="W", stable_identifier=f"S{Woman.objects.count()}")
    ep = PregnancyEpisode.objects.create(woman=woman, facility=facility)
    intake = Intake.objects.create(
        facility=facility, submitted_by=officer, register_family="Delivery", source_hash=f"h{Intake.objects.count()}",
        batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 1, 31),
    )
    row = SourceRow.objects.create(intake=intake, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})
    BirthEvent.objects.create(episode=ep, woman=woman, facility=facility, source_row=row, data={}, delivery_date=D(2026, 1, 10), still_birth=False)


def _anc(facility, officer, parity):
    woman = Woman.objects.create(facility=facility, name="W", stable_identifier=f"S{Woman.objects.count()}")
    ep = PregnancyEpisode.objects.create(woman=woman, facility=facility)
    intake = Intake.objects.create(
        facility=facility, submitted_by=officer, register_family="ANC", source_hash=f"h{Intake.objects.count()}",
        batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 1, 31),
    )
    row = SourceRow.objects.create(intake=intake, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})
    ANCContact.objects.create(episode=ep, woman=woman, facility=facility, source_row=row, data={"parity": parity, "hiv_result": "NR"}, service_date=D(2026, 1, 10))


@pytest.mark.django_db
def test_facility_league_ranks_higher_first(geo):
    _, _, f1, f2, officer = geo
    _birth(f1, officer, 1)
    _birth(f1, officer, 2)  # f1 has 2 deliveries
    _birth(f2, officer, 1)  # f2 has 1
    league = facility_league([f1.id, f2.id], metric="deliveries")
    assert league["rows"][0]["facility_id"] == str(f1.id)
    assert league["rows"][0]["value"] == 2
    assert league["rows"][1]["value"] == 1


@pytest.mark.django_db
def test_geo_rollup_sums_to_state(geo):
    state, _, f1, f2, officer = geo
    _birth(f1, officer, 1)
    _birth(f2, officer, 1)
    roll = geo_rollup([f1.id, f2.id], metric="deliveries", level="state")
    assert len(roll["areas"]) == 1
    assert roll["areas"][0]["name"] == "Kano"
    assert roll["areas"][0]["value"] == 2


@pytest.mark.django_db
def test_equity_by_parity_bands(geo):
    _, _, f1, _f2, officer = geo
    _anc(f1, officer, 0)   # nulliparous
    _anc(f1, officer, 3)   # 1-4
    _anc(f1, officer, 6)   # grand multipara
    eq = equity_by_parity([f1.id])
    bands = {b["band"] for b in eq["bands"]}
    assert "0 (nulliparous)" in bands
    assert "1–4" in bands
    assert "5+ (grand multipara)" in bands
    # Every contact has screening recorded → 100%.
    for b in eq["bands"]:
        assert b["screening_coverage"]["rate"] == 1.0
