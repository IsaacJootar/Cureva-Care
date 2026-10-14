"""Identity-matching update — Sections B, C, E (IDENTITY_MATCHING_UPDATE.md)."""
import datetime
import uuid

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.identity import confirm_candidate, resolve_identity
from maternal_projection.models import (
    CandidateStatus,
    IdentityCandidate,
    SourceRowLink,
    Woman,
    WomanIdentifier,
)


@pytest.fixture
def facility(db):
    s = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=s, name="Nassarawa")
    w = Ward.objects.create(local_government=lga, name="Gama")
    return Facility.objects.create(ward=w, name="Gama PHC")


@pytest.fixture
def facility_b(db, facility):
    lga = LocalGovernment.objects.create(state=facility.ward.local_government.state, name="Fagge")
    w = Ward.objects.create(local_government=lga, name="Sabon Gari")
    return Facility.objects.create(ward=w, name="Fagge PHC")


@pytest.fixture
def officer(db):
    return User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)


@pytest.fixture
def lead(db, facility):
    return User.objects.create_user(email="lead@x.com", name="Lead", role=Role.FACILITY_LEAD, facility=facility)


def row(facility, officer, normalized, svc, family="ANC"):
    intake = Intake.objects.create(
        facility=facility, submitted_by=officer, register_family=family, source_hash=uuid.uuid4().hex,
        batch_period_from=svc, batch_period_to=svc,
    )
    return SourceRow.objects.create(
        intake=intake, row_number=1, raw_payload={}, normalized=normalized,
        service_date=svc, status="verified", extraction_confidence={},
    )


D = datetime.date


def test_same_number_similar_name_recent_links(facility, officer):
    r1 = row(facility, officer, {"card_number": "1047", "name": "Fatima Bello"}, D(2026, 1, 10))
    assert resolve_identity(r1)["method"] == "strict"
    woman = SourceRowLink.objects.get(source_row=r1).woman

    r2 = row(facility, officer, {"card_number": "1047", "name": "Mrs Fatima Bello"}, D(2026, 2, 10))
    result = resolve_identity(r2)
    assert result["method"] == "strict"
    assert SourceRowLink.objects.get(source_row=r2).woman_id == woman.id


def test_same_number_different_name_goes_to_review(facility, officer):
    r1 = row(facility, officer, {"card_number": "1047", "name": "Fatima Bello"}, D(2026, 1, 10))
    resolve_identity(r1)
    r2 = row(facility, officer, {"card_number": "1047", "name": "Grace Okafor"}, D(2026, 2, 10))
    result = resolve_identity(r2)
    assert result["method"] == "review" and result["reason"] == "card_match_name_conflict"
    assert not SourceRowLink.objects.filter(source_row=r2).exists()
    assert IdentityCandidate.objects.get(source_row=r2).reason == "card_match_name_conflict"


def test_same_number_name_missing_goes_to_review(facility, officer):
    r1 = row(facility, officer, {"card_number": "1047", "name": "Fatima Bello"}, D(2026, 1, 10))
    resolve_identity(r1)
    r2 = row(facility, officer, {"card_number": "1047"}, D(2026, 2, 10))  # no name on this row
    result = resolve_identity(r2)
    assert result["reason"] == "card_match_name_missing"


def test_stale_card_match_goes_to_review(facility, officer):
    r1 = row(facility, officer, {"card_number": "1047", "name": "Fatima Bello"}, D(2025, 1, 1))
    resolve_identity(r1)
    r2 = row(facility, officer, {"card_number": "1047", "name": "Fatima Bello"}, D(2026, 6, 1))  # >365 days later
    result = resolve_identity(r2)
    assert result["reason"] == "card_match_stale"


def test_same_number_different_facility_never_links(facility, facility_b, officer):
    r1 = row(facility, officer, {"card_number": "1047", "name": "Fatima Bello"}, D(2026, 1, 10))
    resolve_identity(r1)
    r2 = row(facility_b, officer, {"card_number": "1047", "name": "Fatima Bello"}, D(2026, 2, 10))
    resolve_identity(r2)
    # A separate woman at facility B — never linked across facilities.
    assert Woman.objects.filter(facility=facility).count() == 1
    assert Woman.objects.filter(facility=facility_b).count() == 1
    assert SourceRowLink.objects.get(source_row=r2).woman.facility_id == facility_b.id


def test_new_card_for_known_woman_reviews_then_future_strict_links(facility, officer, lead):
    # Pregnancy 1: card 1047, Fatima.
    r1 = row(facility, officer, {"card_number": "1047", "name": "Fatima Bello", "phone": "08031112222"}, D(2025, 1, 10))
    resolve_identity(r1)
    woman = SourceRowLink.objects.get(source_row=r1).woman

    # Pregnancy 2: NEW card 2050, same name AND phone → recognised as likely
    # the same woman, so it goes to review (not a silent duplicate).
    r2 = row(facility, officer, {"card_number": "2050", "name": "Fatima Bello", "phone": "08031112222"}, D(2026, 2, 10))
    res2 = resolve_identity(r2)
    assert res2["method"] == "candidates_created"
    assert Woman.objects.count() == 1  # no duplicate woman
    cand = IdentityCandidate.objects.get(source_row=r2)

    # Facility lead confirms → 2050 is now on her record.
    confirm_candidate(cand, lead)
    assert WomanIdentifier.objects.filter(woman=woman, value="2050").exists()

    # A later row carrying 2050 now links on the strict path.
    r3 = row(facility, officer, {"card_number": "2050", "name": "Fatima Bello"}, D(2026, 5, 1))
    assert resolve_identity(r3)["method"] == "strict"
    assert SourceRowLink.objects.get(source_row=r3).woman_id == woman.id


def test_phone_alone_never_links(facility, officer):
    r1 = row(facility, officer, {"card_number": "1047", "name": "Fatima Bello", "phone": "08031112222"}, D(2026, 1, 10))
    resolve_identity(r1)
    # A row with ONLY a phone (no card, no name) must not link.
    r2 = row(facility, officer, {"phone": "08031112222"}, D(2026, 2, 10))
    result = resolve_identity(r2)
    assert not SourceRowLink.objects.filter(source_row=r2).exists()
    assert result["method"] in ("unlinked_encounter", "candidates_created")
    # Even if a candidate is raised, nothing links without human confirmation.
    assert IdentityCandidate.objects.filter(source_row=r2, status=CandidateStatus.CONFIRMED).count() == 0


def test_one_digit_misread_never_silently_links_to_a_different_woman(facility, officer):
    # Two different women with adjacent card numbers.
    resolve_identity(row(facility, officer, {"card_number": "1047", "name": "Fatima Bello"}, D(2026, 1, 10)))
    resolve_identity(row(facility, officer, {"card_number": "1041", "name": "Grace Okafor"}, D(2026, 1, 11)))
    # A misread: Grace's row read as 1047 (Fatima's number) but the name is Grace.
    misread = row(facility, officer, {"card_number": "1047", "name": "Grace Okafor"}, D(2026, 2, 1))
    result = resolve_identity(misread)
    # The name disagreement stops the silent link — it goes to review instead.
    assert not SourceRowLink.objects.filter(source_row=misread).exists()
    assert result["reason"] == "card_match_name_conflict"


def test_cross_register_anc_number_links_delivery(facility, officer, lead):
    # ANC row establishes Fatima with ANC card 1047.
    anc = row(facility, officer, {"card_number": "1047", "name": "Fatima Bello"}, D(2026, 1, 10), family="ANC")
    resolve_identity(anc)
    woman = SourceRowLink.objects.get(source_row=anc).woman

    # Delivery row carries its own number 9001 AND her ANC number 1047.
    delivery = row(facility, officer, {"card_number": "9001", "anc_number": "1047", "name": "Fatima Bello"}, D(2026, 9, 1), family="Delivery")
    result = resolve_identity(delivery)
    assert result["method"] == "strict"
    assert SourceRowLink.objects.get(source_row=delivery).woman_id == woman.id
    # The delivery's own number is now on her record too.
    assert WomanIdentifier.objects.filter(woman=woman, value="9001").exists()
