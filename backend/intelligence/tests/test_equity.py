"""Equity engine (expansion M6)."""
import datetime

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import ANCContact, PregnancyEpisode, Woman
from intelligence.equity import equity_breakdown

D = datetime.date


@pytest.fixture
def facility(db):
    s = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=s, name="Nassarawa")
    w = Ward.objects.create(local_government=lga, name="Gama")
    f = Facility.objects.create(ward=w, name="Gama PHC")
    officer = User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)
    return f, officer


def _anc(f, officer, *, parity, age, screened):
    woman = Woman.objects.create(facility=f, name="W", stable_identifier=f"S{Woman.objects.count()}", age=age)
    ep = PregnancyEpisode.objects.create(woman=woman, facility=f, booking_date=D(2026, 1, 5))
    intake = Intake.objects.create(facility=f, submitted_by=officer, register_family="ANC", source_hash=f"h{Intake.objects.count()}", batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 1, 31))
    row = SourceRow.objects.create(intake=intake, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})
    data = {"parity": parity}
    if screened:
        data["hiv_result"] = "NR"
    ANCContact.objects.create(episode=ep, woman=woman, facility=f, source_row=row, data=data, service_date=D(2026, 1, 10))


@pytest.mark.django_db
def test_equity_by_parity_with_gap(facility):
    f, officer = facility
    # First-timers: 6 contacts, 2 screened = 33%. 5+ births: 6 contacts, 6 screened = 100%.
    for _ in range(6):
        _anc(f, officer, parity=0, age=19, screened=False)
    for i in range(6):
        _anc(f, officer, parity=0, age=19, screened=(i < 2))
    for _ in range(6):
        _anc(f, officer, parity=6, age=40, screened=True)

    data = equity_breakdown([f.id], dimension="parity", metric="screening")
    groups = {g["group"]: g for g in data["groups"]}
    assert groups["First pregnancy (0 past births)"]["denominator"] == 12
    assert groups["First pregnancy (0 past births)"]["rate"] == round(2 / 12, 4)
    assert groups["5+ past births"]["rate"] == 1.0
    assert data["gap"]["worst"] == "First pregnancy (0 past births)"
    assert data["gap"]["best"] == "5+ past births"
    assert data["gap"]["points"] == round((1.0 - 2 / 12) * 100, 1)


@pytest.mark.django_db
def test_equity_by_age_bands(facility):
    f, officer = facility
    for _ in range(5):
        _anc(f, officer, parity=1, age=18, screened=True)
    for _ in range(5):
        _anc(f, officer, parity=1, age=40, screened=False)
    data = equity_breakdown([f.id], dimension="age", metric="screening")
    groups = {g["group"]: g for g in data["groups"]}
    assert groups["Under 20"]["rate"] == 1.0
    assert groups["35 or older"]["rate"] == 0.0
    # order follows the age band order
    assert [g["group"] for g in data["groups"]][:2] == ["Under 20", "20–34"] or data["groups"][0]["group"] == "Under 20"


@pytest.mark.django_db
def test_small_groups_flagged_and_excluded_from_gap(facility):
    f, officer = facility
    # One tiny group (2 contacts) at 100% must not define the gap.
    for _ in range(2):
        _anc(f, officer, parity=0, age=19, screened=True)
    for _ in range(8):
        _anc(f, officer, parity=6, age=40, screened=True)
    data = equity_breakdown([f.id], dimension="parity", metric="screening")
    first = next(g for g in data["groups"] if g["group"].startswith("First"))
    assert first["low_confidence"] is True
    # only one adequate group -> no gap computed
    assert data["gap"] is None
