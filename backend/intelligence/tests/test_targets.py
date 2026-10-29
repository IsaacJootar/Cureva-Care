"""Goals & Targets engine (expansion M7)."""
import datetime

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import ANCContact, PregnancyEpisode, Woman
from intelligence.models import ProgramTarget
from intelligence.targets import target_progress

D = datetime.date


@pytest.fixture
def facility(db):
    state = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=state, name="Nassarawa")
    ward = Ward.objects.create(local_government=lga, name="Gama")
    f = Facility.objects.create(ward=ward, name="Gama PHC")
    officer = User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)
    return f, officer


def _episode(facility, officer, anc_contacts):
    woman = Woman.objects.create(facility=facility, name="W", stable_identifier=f"S{Woman.objects.count()}")
    ep = PregnancyEpisode.objects.create(woman=woman, facility=facility, booking_date=D(2026, 1, 5))
    for _ in range(anc_contacts):
        intake = Intake.objects.create(facility=facility, submitted_by=officer, register_family="ANC", source_hash=f"h{Intake.objects.count()}", batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 1, 31))
        row = SourceRow.objects.create(intake=intake, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})
        ANCContact.objects.create(episode=ep, woman=woman, facility=facility, source_row=row, data={}, service_date=D(2026, 1, 10))
    return ep


@pytest.mark.django_db
def test_anc4_goal_on_and_off_track(facility):
    f, officer = facility
    _episode(f, officer, anc_contacts=5)  # reaches 4+
    _episode(f, officer, anc_contacts=1)  # does not
    # 1 of 2 registered reached 4+ => 50%.
    ProgramTarget.objects.update_or_create(key="anc4_of_registered", defaults={"target_pct": 80, "is_active": True, "order": 1})
    # deactivate the others so only this goal is assessed
    ProgramTarget.objects.exclude(key="anc4_of_registered").update(is_active=False)

    data = target_progress([f.id])
    goal = next(g for g in data["goals"] if g["key"] == "anc4_of_registered")
    assert goal["current_pct"] == 50.0
    assert goal["target_pct"] == 80
    assert goal["on_track"] is False

    # Lower the target below current -> on track.
    ProgramTarget.objects.filter(key="anc4_of_registered").update(target_pct=40)
    goal = next(g for g in target_progress([f.id])["goals"] if g["key"] == "anc4_of_registered")
    assert goal["on_track"] is True


@pytest.mark.django_db
def test_inactive_targets_are_excluded(facility):
    f, officer = facility
    _episode(f, officer, anc_contacts=4)
    ProgramTarget.objects.all().update(is_active=False)
    assert target_progress([f.id])["goals"] == []
