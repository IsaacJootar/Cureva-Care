"""Section D/E — pregnancy episode rules (IDENTITY_MATCHING_UPDATE.md)."""
import datetime
import uuid

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import (
    ANCContact,
    LinkMethod,
    PNCContact,
    PregnancyEpisode,
    SourceRowLink,
    Woman,
)
from maternal_projection.projection import project_row

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


def linked_row(woman, facility, officer, family, norm, svc):
    intake = Intake.objects.create(
        facility=facility, submitted_by=officer, register_family=family, source_hash=uuid.uuid4().hex,
        batch_period_from=svc, batch_period_to=svc,
    )
    r = SourceRow.objects.create(
        intake=intake, row_number=1, raw_payload={}, normalized=norm,
        service_date=svc, status="verified", extraction_confidence={},
    )
    SourceRowLink.objects.create(source_row=r, woman=woman, method=LinkMethod.STRICT)
    project_row(r)
    return r


@pytest.mark.django_db
def test_booking_after_delivery_opens_new_episode(facility, officer):
    woman = Woman.objects.create(facility=facility, name="Fatima", stable_identifier="C1")
    linked_row(woman, facility, officer, "ANC", {"booking_date": "2025-01-10", "gestational_age_weeks": "10"}, D(2025, 1, 10))
    linked_row(woman, facility, officer, "Delivery", {"delivery_date": "2025-10-01", "mode_of_delivery": "SVD"}, D(2025, 10, 1))
    # A booking after that delivery is a new pregnancy.
    linked_row(woman, facility, officer, "ANC", {"booking_date": "2026-02-01", "gestational_age_weeks": "9"}, D(2026, 2, 1))
    assert PregnancyEpisode.objects.filter(woman=woman).count() == 2


@pytest.mark.django_db
def test_normal_follow_up_attaches_to_open_episode(facility, officer):
    woman = Woman.objects.create(facility=facility, name="Amina", stable_identifier="C2")
    linked_row(woman, facility, officer, "ANC", {"booking_date": "2025-01-10", "gestational_age_weeks": "10"}, D(2025, 1, 10))
    linked_row(woman, facility, officer, "ANC", {"gestational_age_weeks": "16"}, D(2025, 3, 10))
    assert PregnancyEpisode.objects.filter(woman=woman).count() == 1
    ep = PregnancyEpisode.objects.get(woman=woman)
    assert ANCContact.objects.filter(episode=ep).count() == 2


@pytest.mark.django_db
def test_visit_long_after_booking_with_no_outcome_opens_new_episode(facility, officer):
    woman = Woman.objects.create(facility=facility, name="Zainab", stable_identifier="C3")
    linked_row(woman, facility, officer, "ANC", {"booking_date": "2025-01-10", "gestational_age_weeks": "10"}, D(2025, 1, 10))
    # 365 days later, no recorded outcome → too long for the same pregnancy.
    linked_row(woman, facility, officer, "ANC", {"booking_date": "2026-01-10", "gestational_age_weeks": "9"}, D(2026, 1, 10))
    assert PregnancyEpisode.objects.filter(woman=woman).count() == 2


@pytest.mark.django_db
def test_pnc_attaches_to_episode_with_a_delivery(facility, officer):
    woman = Woman.objects.create(facility=facility, name="Grace", stable_identifier="C4")
    linked_row(woman, facility, officer, "ANC", {"booking_date": "2025-01-10"}, D(2025, 1, 10))
    linked_row(woman, facility, officer, "Delivery", {"delivery_date": "2025-10-01", "mode_of_delivery": "SVD"}, D(2025, 10, 1))
    pnc = linked_row(woman, facility, officer, "PNC", {"visit_date": "2025-10-15", "subject": "mother"}, D(2025, 10, 15))
    contact = PNCContact.objects.get(source_row=pnc)
    ep = PregnancyEpisode.objects.get(woman=woman)
    assert contact.episode_id == ep.id
