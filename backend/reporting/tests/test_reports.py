"""Report products (WS7)."""
import datetime

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import ANCContact, BirthEvent, PregnancyEpisode, Woman
from reporting.generator import REPORT_TYPES, build_report

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


def _seed(facility, officer):
    woman = Woman.objects.create(facility=facility, name="Amina", stable_identifier="S1")
    ep = PregnancyEpisode.objects.create(woman=woman, facility=facility, booking_date=D(2026, 1, 5), booking_gestational_age_weeks=10)
    intake = Intake.objects.create(facility=facility, submitted_by=officer, register_family="ANC", source_hash="h1", batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 1, 31))
    ANCContact.objects.create(episode=ep, woman=woman, facility=facility, source_row=SourceRow.objects.create(intake=intake, row_number=1, raw_payload={}, normalized={"hiv_result": "NR"}, status="verified", extraction_confidence={}), data={"hiv_result": "NR"}, service_date=D(2026, 2, 1))
    di = Intake.objects.create(facility=facility, submitted_by=officer, register_family="Delivery", source_hash="h2", batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 6, 30))
    BirthEvent.objects.create(episode=ep, woman=woman, facility=facility, source_row=SourceRow.objects.create(intake=di, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={}), data={}, delivery_date=D(2026, 6, 1), still_birth=True)


@pytest.mark.django_db
def test_report_types_assemble_distinct_sections(facility, officer):
    _seed(facility, officer)

    fac_op = build_report("facility_operational", [facility.id])
    assert fac_op["report_type"] == "facility_operational"

    ngo = build_report("ngo_grant", [facility.id])
    assert ngo["report_type"] == "ngo_grant"
    assert "equity_by_parity" in ngo and "data_quality_rdqa" in ngo

    gov = build_report("government_surveillance", [facility.id])
    assert gov["report_type"] == "government_surveillance"
    # The seeded stillbirth shows up in the surveillance report (counts only).
    assert gov["severe_outcomes"]["count"] == 1
    assert "continuum_funnel" in gov


@pytest.mark.django_db
def test_unknown_type_falls_back(facility, officer):
    _seed(facility, officer)
    r = build_report("nonsense", [facility.id])
    assert r["report_type"] == "facility_operational"


def test_report_types_catalogue():
    assert set(REPORT_TYPES) == {"facility_operational", "ngo_grant", "government_surveillance"}
