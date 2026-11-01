"""Early warning engine (expansion M3)."""
import datetime

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import ANCContact, BirthEvent, PregnancyEpisode, Woman
from intelligence.early_warning import early_warnings

D = datetime.date


@pytest.fixture
def geo(db):
    s = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=s, name="Nassarawa")
    w = Ward.objects.create(local_government=lga, name="Gama")
    officer = User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)
    return lga, w, officer


def _fac(w, name):
    return Facility.objects.create(ward=w, name=name)


def _row(f, officer):
    ik = Intake.objects.create(facility=f, submitted_by=officer, register_family="ANC", source_hash=f"h{Intake.objects.count()}", batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 6, 30))
    return SourceRow.objects.create(intake=ik, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})


def _anc(f, officer, month, n):
    for _ in range(n):
        woman = Woman.objects.create(facility=f, name="W", stable_identifier=f"S{Woman.objects.count()}")
        ANCContact.objects.create(woman=woman, facility=f, source_row=_row(f, officer), data={}, service_date=D(2026, month, 10))


def _birth(f, officer, month, *, still=False):
    woman = Woman.objects.create(facility=f, name="W", stable_identifier=f"S{Woman.objects.count()}")
    BirthEvent.objects.create(woman=woman, facility=f, source_row=_row(f, officer), data={}, delivery_date=D(2026, month, 20), still_birth=still, maternal_outcome="alive")


@pytest.mark.django_db
def test_activity_falling(geo):
    lga, w, officer = geo
    f = _fac(w, "Falling PHC")
    for m in (1, 2, 3, 4, 5):
        _anc(f, officer, m, 10)
    _anc(f, officer, 6, 2)  # sharp drop in the most recent month
    d = early_warnings([f.id])
    item = next(x for x in d["watch"] if x["facility_id"] == str(f.id))
    assert item["type"] == "activity_falling" and item["severity"] == "high"


@pytest.mark.django_db
def test_gone_quiet(geo):
    lga, w, officer = geo
    f = _fac(w, "Quiet PHC")
    # reported Jan–Apr, then silence; needs another facility to set the window end.
    other = _fac(w, "Active PHC")
    for m in (1, 2, 3, 4, 5, 6):
        _anc(other, officer, m, 6)
    for m in (1, 2, 3, 4):
        _anc(f, officer, m, 6)
    d = early_warnings([f.id, other.id])
    item = next(x for x in d["watch"] if x["facility_id"] == str(f.id))
    assert item["type"] == "gone_quiet"


@pytest.mark.django_db
def test_severe_rising(geo):
    lga, w, officer = geo
    f = _fac(w, "Rising PHC")
    for m in (1, 2, 3):
        _anc(f, officer, m, 6)
        _birth(f, officer, m)              # births, no deaths early
    for m in (4, 5, 6):
        _anc(f, officer, m, 6)
        _birth(f, officer, m)
        _birth(f, officer, m, still=True)  # stillbirths climbing late
    d = early_warnings([f.id])
    types = [x["type"] for x in d["watch"] if x["facility_id"] == str(f.id)]
    assert "severe_rising" in types


@pytest.mark.django_db
def test_stable_facility_has_no_warning(geo):
    lga, w, officer = geo
    f = _fac(w, "Steady PHC")
    for m in (1, 2, 3, 4, 5, 6):
        _anc(f, officer, m, 8)
    d = early_warnings([f.id])
    assert all(x["facility_id"] != str(f.id) for x in d["watch"])
