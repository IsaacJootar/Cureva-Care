"""Golden-file pipeline tests — the Module 2 exit condition (08-delivery-plan).

Driven by a deterministic MockExtractor through the real pipeline: ANC/Delivery/
PNC, a facility-specific override, a low-confidence batch that only publishes
after confirmation, a mis-declared batch held by the cross-check (then switched),
an extraction-provider failure that recovers on retry, and duplicate no-op.
"""
import datetime

import pytest
from django.db import IntegrityError, transaction

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.extraction import MockExtractor
from register_intake.models import (
    Intake,
    IntakeStatus,
    RegisterMismatchStatus,
    SourceRowStatus,
    Template,
)
from register_intake.pipeline import process_intake, resolve_register_mismatch, row_needs_confirmation
from register_intake.publish import PublishError, confirm_field, intake_publishable, publish_intake
from identity_access.services import get_setting
from identity_access.settings_registry import AI_EXTRACTION_CONFIDENCE_THRESHOLD

IMAGES = [b"fake-page-1"]


@pytest.fixture
def facility(db):
    state = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=state, name="Nassarawa")
    ward = Ward.objects.create(local_government=lga, name="Gama")
    return Facility.objects.create(ward=ward, name="Gama PHC")


@pytest.fixture
def officer(db):
    return User.objects.create_user(email="do@example.com", name="DO", role=Role.DATA_OFFICER)


def make_intake(facility, officer, family, source_hash="h1"):
    return Intake.objects.create(
        facility=facility,
        submitted_by=officer,
        register_family=family,
        source_hash=source_hash,
        batch_period_from=datetime.date(2026, 1, 1),
        batch_period_to=datetime.date(2026, 1, 31),
    )


ANC_ROWS = [
    {
        "fields": {"Card No": "A100", "LMP": "01/02/2026", "Gravida": "2", "Parity": "1", "BP": "120/80"},
        "confidence": {"Card No": 0.99, "LMP": 0.95, "Gravida": 0.60, "Parity": 0.92, "BP": 0.90},
    }
]

DELIVERY_ROWS = [
    {
        "fields": {"Card No": "D1", "Date of Delivery": "03/02/2026", "Mode of Delivery": "SVD",
                   "Place of Delivery": "Facility", "Birth Attendant": "Midwife", "Birth Weight": "3.2", "Stillbirth": "No"},
        "confidence": {"Card No": 0.98, "Date of Delivery": 0.96, "Mode of Delivery": 0.97,
                       "Place of Delivery": 0.95, "Birth Attendant": 0.9, "Birth Weight": 0.93, "Stillbirth": 0.95},
    }
]

PNC_ROWS = [
    {
        "fields": {"Card No": "P1", "Visit Date": "05/02/2026", "Days Postpartum": "3", "Subject": "mother",
                   "Maternal Assessment": "Stable", "Feeding": "Exclusive breastfeeding", "Danger Signs": "None"},
        "confidence": {"Card No": 0.98, "Visit Date": 0.95, "Days Postpartum": 0.9, "Subject": 0.95,
                       "Maternal Assessment": 0.9, "Feeding": 0.9, "Danger Signs": 0.92},
    }
]


@pytest.mark.django_db
def test_anc_batch_holds_until_low_confidence_confirmed_then_publishes(facility, officer):
    intake = make_intake(facility, officer, "ANC")
    result = process_intake(intake, IMAGES, MockExtractor(ANC_ROWS))
    assert result["status"] == "rows_created"

    row = intake.rows.get()
    threshold = float(get_setting(AI_EXTRACTION_CONFIDENCE_THRESHOLD))
    # Gravida was read at 0.60 (< 0.85) — it must block publish.
    assert "gravida" in row_needs_confirmation(row, threshold)

    ok, reason = intake_publishable(intake)
    assert not ok and "gravida" in reason

    with pytest.raises(PublishError):
        publish_intake(intake, officer)

    # Confirm the low-confidence field, then publish succeeds.
    confirm_field(row, "gravida", None, officer, correct=False)
    out = publish_intake(intake, officer)
    assert out["status"] == "published"
    intake.refresh_from_db()
    assert intake.status == IntakeStatus.PUBLISHED
    assert intake.rows.get().status == SourceRowStatus.VERIFIED


@pytest.mark.django_db
def test_publish_is_idempotent(facility, officer):
    intake = make_intake(facility, officer, "ANC")
    process_intake(intake, IMAGES, MockExtractor(ANC_ROWS))
    confirm_field(intake.rows.get(), "gravida", None, officer, correct=False)
    first = publish_intake(intake, officer)
    second = publish_intake(intake, officer)
    assert first["already"] is False
    assert second["already"] is True


@pytest.mark.django_db
def test_delivery_and_pnc_batches_process(facility, officer):
    d = make_intake(facility, officer, "Delivery", source_hash="d")
    assert process_intake(d, IMAGES, MockExtractor(DELIVERY_ROWS))["status"] == "rows_created"
    assert d.rows.get().normalized["mode_of_delivery"] == "SVD"

    p = make_intake(facility, officer, "PNC", source_hash="p")
    assert process_intake(p, IMAGES, MockExtractor(PNC_ROWS))["status"] == "rows_created"
    assert p.rows.get().normalized["subject"] == "mother"


@pytest.mark.django_db
def test_facility_specific_template_override_is_used(facility, officer):
    Template.objects.create(
        register_family="ANC", facility=facility, version=1,
        effective_date=datetime.date(2026, 1, 1), is_active=True,
        schema={"register_family": "ANC", "version": 1, "columns": [
            {"canonical_field": "card_number", "label": "Card No", "type": "string", "required": True, "aliases": ["Card No"]},
        ]},
    )
    intake = make_intake(facility, officer, "ANC")
    process_intake(intake, IMAGES, MockExtractor(ANC_ROWS))
    intake.refresh_from_db()
    assert intake.template.facility_id == facility.id  # override, not shared default


@pytest.mark.django_db
def test_misdeclared_delivery_as_anc_is_held_then_switched(facility, officer):
    intake = make_intake(facility, officer, "ANC")  # declared ANC...
    result = process_intake(intake, IMAGES, MockExtractor(DELIVERY_ROWS))  # ...but it's a Delivery page
    assert result["status"] == "held_mismatch"
    assert result["suspected_register_family"] == "Delivery"

    intake.refresh_from_db()
    assert intake.register_mismatch_status == RegisterMismatchStatus.FLAGGED
    # Held: cannot publish while flagged.
    ok, reason = intake_publishable(intake)
    assert not ok and "mismatch" in reason.lower()

    # Switch to the suspected family and re-run.
    resolve_register_mismatch(intake, "switch", officer, IMAGES, MockExtractor(DELIVERY_ROWS))
    intake.refresh_from_db()
    assert intake.register_family == "Delivery"
    assert intake.register_mismatch_status == RegisterMismatchStatus.SWITCHED
    assert intake.rows.get().normalized["mode_of_delivery"] == "SVD"


@pytest.mark.django_db
def test_confirm_declared_clears_the_hold(facility, officer):
    # A legitimately reused label: officer confirms the declared family is right.
    intake = make_intake(facility, officer, "ANC")
    process_intake(intake, IMAGES, MockExtractor(DELIVERY_ROWS))
    assert intake.register_mismatch_status == RegisterMismatchStatus.FLAGGED
    resolve_register_mismatch(intake, "confirm_declared", officer, IMAGES, MockExtractor(DELIVERY_ROWS))
    intake.refresh_from_db()
    assert intake.register_mismatch_status == RegisterMismatchStatus.CONFIRMED_AS_DECLARED
    assert intake.register_family == "ANC"  # unchanged


@pytest.mark.django_db
def test_extraction_failure_lands_on_failed_then_recovers_on_retry(facility, officer):
    intake = make_intake(facility, officer, "ANC")
    result = process_intake(intake, IMAGES, MockExtractor([], fail=True))
    assert result["status"] == "extraction_failed"
    intake.refresh_from_db()
    assert intake.status == IntakeStatus.EXTRACTION_FAILED
    assert intake.rows.count() == 0

    # Retry with a working extractor recovers — nothing was lost.
    process_intake(intake, IMAGES, MockExtractor(ANC_ROWS))
    intake.refresh_from_db()
    assert intake.status == IntakeStatus.AWAITING_CONFIRMATION
    assert intake.rows.count() == 1


@pytest.mark.django_db
def test_duplicate_checksum_is_rejected(facility, officer):
    make_intake(facility, officer, "ANC", source_hash="dup")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_intake(facility, officer, "ANC", source_hash="dup")
