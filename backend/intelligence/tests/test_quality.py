"""Quality-of-care engine (expansion M4)."""
import datetime

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import ANCContact, BirthEvent, PregnancyEpisode, Woman
from intelligence.quality import quality_scorecard

D = datetime.date


@pytest.fixture
def facility(db):
    s = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=s, name="Nassarawa")
    w = Ward.objects.create(local_government=lga, name="Gama")
    f = Facility.objects.create(ward=w, name="Gama PHC")
    officer = User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)
    return f, officer


def _row(f, officer, fam):
    ik = Intake.objects.create(facility=f, submitted_by=officer, register_family=fam, source_hash=f"h{Intake.objects.count()}", batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 1, 31))
    return SourceRow.objects.create(intake=ik, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})


@pytest.mark.django_db
def test_standards_and_gaps(facility):
    f, officer = facility
    woman = Woman.objects.create(facility=f, name="W", stable_identifier="S1")
    ep = PregnancyEpisode.objects.create(woman=woman, facility=f, booking_date=D(2026, 1, 5))
    # 4 ANC contacts: all have iron+tetanus; 2 have BP; 0 have malaria prevention.
    for i in range(4):
        data = {"iron_folate_given": "yes", "tetanus_given": "yes", "hiv_result": "NR", "syphilis_result": "NR", "haemoglobin": "12"}
        if i < 2:
            data["blood_pressure"] = "120/80"
        ANCContact.objects.create(episode=ep, woman=woman, facility=f, source_row=_row(f, officer, "ANC"), data=data, service_date=D(2026, 1, 10 + i))
    # 2 births: 1 skilled attendant, both weighed.
    for i in range(2):
        BirthEvent.objects.create(episode=ep, woman=woman, facility=f, source_row=_row(f, officer, "Delivery"), data={}, delivery_date=D(2026, 1, 20), still_birth=False, attendant_category=("midwife" if i == 0 else "tba"), birth_weight_kg=3.0)

    data = quality_scorecard([f.id])
    s = {x["key"]: x for x in data["standards"]}
    assert s["iron"]["rate"] == 1.0
    assert s["bp"]["rate"] == 0.5                      # 2 of 4
    assert s["malaria"]["rate"] == 0.0                 # recorded nowhere
    assert s["birthweight"]["rate"] == 1.0
    assert s["sba"]["rate"] == 0.5                     # 1 of 2
    assert data["overall_score"] is not None
    # Gaps are the lagging standards, worst first, each with an action.
    gap_keys = [g["key"] for g in data["gaps"]]
    assert gap_keys[0] == "malaria"                    # 0% is worst
    assert "bp" in gap_keys and "sba" in gap_keys
    assert "iron" not in gap_keys                      # 100% is not a gap
    assert all(g.get("action") for g in data["gaps"])


@pytest.mark.django_db
def test_empty_scope():
    assert quality_scorecard([]) == {"overall_score": None, "standards": [], "by_facility": [], "gaps": []}
