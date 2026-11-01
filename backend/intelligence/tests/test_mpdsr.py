"""Death reviews / MPDSR engine (expansion M2)."""
import datetime

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import BirthEvent, PregnancyEpisode, Woman
from intelligence.models import DeathReview
from intelligence.mpdsr import mpdsr_summary, review_queue

D = datetime.date


@pytest.fixture
def facility(db):
    s = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=s, name="Nassarawa")
    w = Ward.objects.create(local_government=lga, name="Gama")
    f = Facility.objects.create(ward=w, name="Gama PHC")
    officer = User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)
    return f, officer


def _death(f, officer, *, still=False, died=False):
    woman = Woman.objects.create(facility=f, name="W", stable_identifier=f"S{Woman.objects.count()}")
    ep = PregnancyEpisode.objects.create(woman=woman, facility=f, booking_date=D(2026, 1, 5))
    ik = Intake.objects.create(facility=f, submitted_by=officer, register_family="Delivery", source_hash=f"h{Intake.objects.count()}", batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 1, 31))
    row = SourceRow.objects.create(intake=ik, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})
    return BirthEvent.objects.create(episode=ep, woman=woman, facility=f, source_row=row, data={}, delivery_date=D(2026, 1, 20), still_birth=still, maternal_outcome=("died" if died else "alive"))


@pytest.mark.django_db
def test_summary_counts_and_review(facility):
    f, officer = facility
    b1 = _death(f, officer, died=True)
    _death(f, officer, still=True)   # unreviewed

    s = mpdsr_summary([f.id])
    assert s["total_deaths"] == 2 and s["reviewed"] == 0 and s["awaiting"] == 2

    DeathReview.objects.create(
        birth_event=b1, facility=f, cause="haemorrhage", avoidable=DeathReview.Avoidable.AVOIDABLE,
        factors=["no_blood", "referral_failed"], action="Set up a blood supply", action_status=DeathReview.ActionStatus.OPEN,
    )
    s = mpdsr_summary([f.id])
    assert s["reviewed"] == 1 and s["awaiting"] == 1
    av = {x["key"]: x["count"] for x in s["avoidable"]}
    assert av["avoidable"] == 1
    fac = {x["key"]: x["count"] for x in s["factors"]}
    assert fac["no_blood"] == 1 and fac["referral_failed"] == 1
    actions = {x["key"]: x["count"] for x in s["actions"]}
    assert actions["open"] == 1 and s["actions_total"] == 1


@pytest.mark.django_db
def test_queue_marks_reviewed(facility):
    f, officer = facility
    b = _death(f, officer, died=True)
    q = review_queue([f.id])
    assert len(q["deaths"]) == 1 and q["deaths"][0]["reviewed"] is False
    assert "Mother died" in q["deaths"][0]["outcomes"]
    assert any(c["key"] == "haemorrhage" for c in q["catalogue"]["causes"])

    DeathReview.objects.create(birth_event=b, facility=f, avoidable=DeathReview.Avoidable.NOT_AVOIDABLE)
    q = review_queue([f.id])
    assert q["deaths"][0]["reviewed"] is True
