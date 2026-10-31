"""Referral pathways & outcomes engine (expansion M5)."""
import datetime

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import Referral, Woman
from intelligence.referrals import referrals_summary

D = datetime.date


@pytest.fixture
def facility(db):
    s = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=s, name="Nassarawa")
    w = Ward.objects.create(local_government=lga, name="Gama")
    f = Facility.objects.create(ward=w, name="Gama PHC")
    officer = User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)
    return f, officer


def _ref(f, officer, *, arrived, status, outcome="", dest="General Hospital", day=15):
    woman = Woman.objects.create(facility=f, name="W", stable_identifier=f"S{Woman.objects.count()}")
    ik = Intake.objects.create(facility=f, submitted_by=officer, register_family="ANC", source_hash=f"h{Intake.objects.count()}", batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 1, 31))
    row = SourceRow.objects.create(intake=ik, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})
    Referral.objects.create(woman=woman, facility=f, source_row=row, origin="ANC", reason="BP", destination=dest, date=D(2026, 1, day), status=status, arrived=arrived, outcome=outcome)


@pytest.mark.django_db
def test_funnel_and_unknown(facility):
    f, officer = facility
    _ref(f, officer, arrived=True, status=Referral.Status.CLOSED, outcome="Treated")   # full loop
    _ref(f, officer, arrived=True, status=Referral.Status.OPEN)                          # arrived, open
    _ref(f, officer, arrived=None, status=Referral.Status.OPEN)                          # lost
    _ref(f, officer, arrived=None, status=Referral.Status.OPEN)                          # lost

    d = referrals_summary([f.id])
    assert d["total"] == 4
    assert d["arrived"] == 2
    assert d["outcome_known"] == 1
    assert d["unknown"] == 2
    steps = {s["label"]: s["value"] for s in d["funnel"]}
    assert steps["Referred to a bigger facility"] == 4
    assert steps["Confirmed she arrived"] == 2
    assert steps["Outcome recorded"] == 1
    assert len(d["lost"]) == 2
    assert d["destinations"][0]["name"] == "General Hospital" and d["destinations"][0]["count"] == 4


@pytest.mark.django_db
def test_facility_loop_closing_rate(facility):
    f, officer = facility
    _ref(f, officer, arrived=True, status=Referral.Status.CLOSED, outcome="ok")
    _ref(f, officer, arrived=None, status=Referral.Status.OPEN)
    d = referrals_summary([f.id])
    fac = d["by_facility"][0]
    assert fac["total"] == 2 and fac["outcome_known"] == 1 and fac["rate"] == 0.5
