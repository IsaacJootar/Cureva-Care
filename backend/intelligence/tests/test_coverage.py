"""Coverage & reach engine (expansion M1)."""
import datetime

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import ANCContact, BirthEvent, PNCContact, PregnancyEpisode, Woman
from intelligence.coverage import coverage
from intelligence.models import CoverageDenominator

D = datetime.date


@pytest.fixture
def geo(db):
    state = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=state, name="Nassarawa")
    ward = Ward.objects.create(local_government=lga, name="Gama")
    f = Facility.objects.create(ward=ward, name="Gama PHC")
    officer = User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)
    return state, lga, ward, f, officer


def _row(facility, officer, family):
    intake = Intake.objects.create(
        facility=facility, submitted_by=officer, register_family=family,
        source_hash=f"h{Intake.objects.count()}",
        batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 1, 31),
    )
    return SourceRow.objects.create(intake=intake, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})


def _episode(facility, anc_contacts=0, delivered=False, pnc=False, officer=None):
    woman = Woman.objects.create(facility=facility, name="W", stable_identifier=f"S{Woman.objects.count()}")
    ep = PregnancyEpisode.objects.create(woman=woman, facility=facility, booking_date=D(2026, 1, 5))
    for _ in range(anc_contacts):
        ANCContact.objects.create(episode=ep, woman=woman, facility=facility, source_row=_row(facility, officer, "ANC"), data={}, service_date=D(2026, 1, 10))
    if delivered:
        BirthEvent.objects.create(episode=ep, woman=woman, facility=facility, source_row=_row(facility, officer, "Delivery"), data={}, delivery_date=D(2026, 1, 20), still_birth=False)
        if pnc:
            PNCContact.objects.create(episode=ep, woman=woman, facility=facility, source_row=_row(facility, officer, "PNC"), data={}, visit_date=D(2026, 1, 27))
    return ep


@pytest.mark.django_db
def test_coverage_rates(geo):
    state, lga, ward, f, officer = geo
    # 4 registered pregnancies: 2 with 4+ ANC, 2 delivered, 1 of those with PNC.
    _episode(f, anc_contacts=5, officer=officer)
    _episode(f, anc_contacts=4, delivered=True, pnc=True, officer=officer)
    _episode(f, anc_contacts=1, delivered=True, officer=officer)
    _episode(f, anc_contacts=0, officer=officer)

    CoverageDenominator.objects.create(
        area_type=CoverageDenominator.AreaType.LOCAL_GOVERNMENT, area_id=lga.id,
        year=2026, expected_pregnancies=10, expected_births=8, source="WorldPop 2026",
    )

    data = coverage([f.id], year=2026, level="lga", indicator="anc1")
    ind = data["indicators"]
    assert ind["anc1"]["numerator"] == 4 and ind["anc1"]["denominator"] == 10 and ind["anc1"]["rate"] == 0.4
    assert ind["anc4"]["numerator"] == 2 and ind["anc4"]["rate"] == 0.2
    assert ind["sba"]["numerator"] == 2 and ind["sba"]["denominator"] == 8 and ind["sba"]["rate"] == 0.25
    assert ind["pnc"]["numerator"] == 1 and ind["pnc"]["rate"] == 0.125
    assert data["sources"] == ["WorldPop 2026"]
    assert data["areas"][0]["name"] == "Nassarawa" and data["areas"][0]["rate"] == 0.4


@pytest.mark.django_db
def test_missing_denominator_yields_no_rate(geo):
    state, lga, ward, f, officer = geo
    _episode(f, anc_contacts=2, officer=officer)
    # No CoverageDenominator loaded for this LGA/year.
    data = coverage([f.id], year=2026, level="lga", indicator="anc1")
    assert data["indicators"]["anc1"]["rate"] is None
    assert data["indicators"]["anc1"]["denominator"] is None
    assert "Nassarawa" in data["areas_missing_denominator"]
    assert data["areas"][0]["has_denominator"] is False


@pytest.mark.django_db
def test_state_rollup_sums_lga_denominators(geo):
    state, lga, ward, f, officer = geo
    lga2 = LocalGovernment.objects.create(state=state, name="Fagge")
    ward2 = Ward.objects.create(local_government=lga2, name="Fagge A")
    f2 = Facility.objects.create(ward=ward2, name="Fagge PHC")
    _episode(f, anc_contacts=1, officer=officer)
    _episode(f2, anc_contacts=1, officer=officer)
    CoverageDenominator.objects.create(area_type=CoverageDenominator.AreaType.LOCAL_GOVERNMENT, area_id=lga.id, year=2026, expected_pregnancies=10, source="x")
    CoverageDenominator.objects.create(area_type=CoverageDenominator.AreaType.LOCAL_GOVERNMENT, area_id=lga2.id, year=2026, expected_pregnancies=20, source="x")

    data = coverage([f.id, f2.id], year=2026, level="state", indicator="anc1")
    assert len(data["areas"]) == 1  # one state
    assert data["areas"][0]["name"] == "Kano"
    assert data["indicators"]["anc1"]["numerator"] == 2 and data["indicators"]["anc1"]["denominator"] == 30
