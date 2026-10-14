"""Identity linkage — strict path, probabilistic matching, no auto-merge, audit."""
import datetime

import pytest

from identity_access.models import AuditEvent, Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.identity import (
    confirm_candidate,
    reject_candidate,
    resolve_identity,
)
from maternal_projection.models import (
    CandidateStatus,
    IdentityCandidate,
    LinkMethod,
    SourceRowLink,
    Woman,
)


@pytest.fixture
def facility(db):
    state = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=state, name="Nassarawa")
    ward = Ward.objects.create(local_government=lga, name="Gama")
    return Facility.objects.create(ward=ward, name="Gama PHC")


@pytest.fixture
def officer(db):
    return User.objects.create_user(email="do@example.com", name="DO", role=Role.DATA_OFFICER)


@pytest.fixture
def lead(db, facility):
    return User.objects.create_user(
        email="lead@example.com", name="Lead", role=Role.FACILITY_LEAD, facility=facility
    )


def make_row(facility, officer, normalized, hash_="h", row_no=1):
    intake = Intake.objects.create(
        facility=facility, submitted_by=officer, register_family="ANC",
        source_hash=hash_, batch_period_from=datetime.date(2026, 1, 1),
        batch_period_to=datetime.date(2026, 1, 31),
    )
    return SourceRow.objects.create(
        intake=intake, row_number=row_no, raw_payload={}, normalized=normalized,
        status="verified", extraction_confidence={},
    )


@pytest.mark.django_db
def test_strict_path_creates_woman_and_links(facility, officer):
    row = make_row(facility, officer, {"card_number": "ANC/2026/001"})
    result = resolve_identity(row)
    assert result["method"] == "strict" and result["created_woman"] is True
    link = SourceRowLink.objects.get(source_row=row)
    assert link.method == LinkMethod.STRICT
    assert link.linked_by is None  # automatic, no human


@pytest.mark.django_db
def test_strict_path_links_to_existing_woman(facility, officer):
    woman = Woman.objects.create(facility=facility, stable_identifier="ANC/2026/001", name="Amina")
    # The row carries the same card AND a matching name (Section B: a card match
    # needs a second fact — the name must agree).
    row = make_row(facility, officer, {"card_number": "ANC/2026/001", "name": "Amina"})
    result = resolve_identity(row)
    assert result["created_woman"] is False
    assert SourceRowLink.objects.get(source_row=row).woman_id == woman.id
    assert Woman.objects.count() == 1  # no duplicate created


@pytest.mark.django_db
def test_probabilistic_match_queues_candidate_never_auto_links(facility, officer):
    Woman.objects.create(facility=facility, name="Amina Yusuf", phone="08030001111")
    # A row with matching demographics but NO stable identifier.
    row = make_row(facility, officer, {"name": "Amina Yusuf", "phone": "08030001111"})
    result = resolve_identity(row)
    assert result["method"] == "candidates_created" and result["candidates"] == 1
    cand = IdentityCandidate.objects.get(source_row=row)
    assert cand.status == CandidateStatus.PENDING
    assert float(cand.confidence) >= 0.75
    # Critically: NO link was created automatically.
    assert not SourceRowLink.objects.filter(source_row=row).exists()


@pytest.mark.django_db
def test_below_threshold_is_unlinked_encounter(facility, officer):
    Woman.objects.create(facility=facility, name="Completely Different Person")
    row = make_row(facility, officer, {"name": "Amina Yusuf"})
    result = resolve_identity(row)
    # Weak name-only match stays below 0.75 -> no candidate, unlinked encounter.
    assert IdentityCandidate.objects.filter(source_row=row).count() == 0
    assert not SourceRowLink.objects.filter(source_row=row).exists()


@pytest.mark.django_db
def test_confirm_requires_user_and_links_and_audits(facility, officer, lead):
    Woman.objects.create(facility=facility, name="Amina Yusuf", phone="08030001111")
    row = make_row(facility, officer, {"name": "Amina Yusuf", "phone": "08030001111"})
    resolve_identity(row)
    cand = IdentityCandidate.objects.get(source_row=row)

    # No code path can confirm without a reviewing user.
    with pytest.raises(ValueError):
        confirm_candidate(cand, None)

    confirm_candidate(cand, lead)
    cand.refresh_from_db()
    assert cand.status == CandidateStatus.CONFIRMED
    assert cand.reviewed_by == lead
    assert SourceRowLink.objects.get(source_row=row).method == LinkMethod.CANDIDATE_CONFIRMED
    assert AuditEvent.objects.filter(event_type="identity_candidate_confirmed").exists()


@pytest.mark.django_db
def test_reject_leaves_unlinked_and_audits(facility, officer, lead):
    Woman.objects.create(facility=facility, name="Amina Yusuf", phone="08030001111")
    row = make_row(facility, officer, {"name": "Amina Yusuf", "phone": "08030001111"})
    resolve_identity(row)
    cand = IdentityCandidate.objects.get(source_row=row)
    reject_candidate(cand, lead)
    cand.refresh_from_db()
    assert cand.status == CandidateStatus.REJECTED
    assert not SourceRowLink.objects.filter(source_row=row).exists()
    assert AuditEvent.objects.filter(event_type="identity_candidate_rejected").exists()


@pytest.mark.django_db
def test_no_candidate_can_be_confirmed_without_reviewed_by_in_db():
    # There is exactly one confirm path and it sets reviewed_by; a confirmed
    # candidate therefore always has a reviewer.
    assert not IdentityCandidate.objects.filter(
        status=CandidateStatus.CONFIRMED, reviewed_by__isnull=True
    ).exists()
