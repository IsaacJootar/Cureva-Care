"""Intake API flow tests (storage + extractor mocked)."""
import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from identity_access import auth_service
from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake import pipeline, storage
from register_intake.extraction import MockExtractor

ANC_ROWS = [
    {
        "fields": {"Card No": "A100", "LMP": "01/02/2026", "Gravida": "2", "Parity": "1"},
        "confidence": {"Card No": 0.99, "LMP": 0.95, "Gravida": 0.60, "Parity": 0.92},
    }
]


@pytest.fixture
def facility(db):
    state = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=state, name="Nassarawa")
    ward = Ward.objects.create(local_government=lga, name="Gama")
    return Facility.objects.create(ward=ward, name="Gama PHC")


@pytest.fixture
def officer(db):
    return User.objects.create_user(email="do@example.com", name="DO", role=Role.DATA_OFFICER)


def client_for(user):
    c = APIClient()
    raw = auth_service.mint_signin_ticket(user)
    access = c.post("/api/v1/auth/session", {"token": raw}, format="json").json()["access"]
    c.credentials(HTTP_AUTHORIZATION="Bearer " + access)
    return c


@pytest.fixture(autouse=True)
def mock_storage_and_extractor(monkeypatch):
    store = {}

    def fake_store(intake_id, page, data, content_type="image/jpeg"):
        key = f"intakes/{intake_id}/{page}"
        store[key] = data
        return key

    monkeypatch.setattr(storage, "store_page", fake_store)
    monkeypatch.setattr(storage, "fetch_page", lambda key: store[key])
    monkeypatch.setattr(pipeline, "default_extractor", lambda: MockExtractor(ANC_ROWS))


def _img(name="anc.jpg", content=b"page-bytes"):
    return SimpleUploadedFile(name, content, content_type="image/jpeg")


@pytest.mark.django_db
def test_full_intake_flow_create_validate_confirm_publish(facility, officer):
    c = client_for(officer)

    create = c.post(
        "/api/v1/intakes",
        {
            "facility": str(facility.id),
            "register_family": "ANC",
            "batch_period_from": "2026-01-01",
            "batch_period_to": "2026-01-31",
            "images": _img(),
        },
        format="multipart",
    )
    assert create.status_code == 201, create.content
    intake_id = create.json()["id"]

    validate = c.post(f"/api/v1/intakes/{intake_id}/validate")
    assert validate.status_code == 200
    assert validate.json()["result"]["status"] == "rows_created"

    rows = c.get(f"/api/v1/intakes/{intake_id}/rows").json()
    assert "gravida" in rows[0]["needs_confirmation"]
    assert "card_number" in rows[0]["needs_confirmation"]  # always-confirm identity field
    row_id = rows[0]["id"]
    pending = rows[0]["needs_confirmation"]

    # Publish blocked until every field needing confirmation is confirmed.
    blocked = c.post(f"/api/v1/intakes/{intake_id}/publish")
    assert blocked.status_code == 409

    for field in pending:
        c.post(
            f"/api/v1/intakes/{intake_id}/rows/{row_id}/confirm-field",
            {"field": field, "correct": False},
            format="json",
        )
    published = c.post(f"/api/v1/intakes/{intake_id}/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"


@pytest.mark.django_db
def test_duplicate_upload_is_a_noop(facility, officer):
    c = client_for(officer)
    payload = {
        "facility": str(facility.id),
        "register_family": "ANC",
        "batch_period_from": "2026-01-01",
        "batch_period_to": "2026-01-31",
    }
    first = c.post("/api/v1/intakes", {**payload, "images": _img(content=b"same")}, format="multipart")
    second = c.post("/api/v1/intakes", {**payload, "images": _img(content=b"same")}, format="multipart")
    assert first.status_code == 201
    assert second.status_code == 200  # no-op, not a re-import
    assert "Duplicate" in second.json()["detail"]


@pytest.mark.django_db
def test_failed_attempt_can_be_reuploaded(facility, officer):
    """A prior attempt that never produced usable data (extraction failed) must
    not permanently block re-uploading the same image."""
    from register_intake.models import Intake, IntakeStatus

    c = client_for(officer)
    payload = {
        "facility": str(facility.id),
        "register_family": "ANC",
        "batch_period_from": "2026-01-01",
        "batch_period_to": "2026-01-31",
    }
    first = c.post("/api/v1/intakes", {**payload, "images": _img(content=b"same")}, format="multipart")
    assert first.status_code == 201
    Intake.objects.filter(id=first.json()["id"]).update(status=IntakeStatus.EXTRACTION_FAILED)

    retry = c.post("/api/v1/intakes", {**payload, "images": _img(content=b"same")}, format="multipart")
    assert retry.status_code == 201  # allowed — the failed attempt is replaced
    assert "Duplicate" not in (retry.json().get("detail") or "")
    assert Intake.objects.filter(facility=facility, register_family="ANC").count() == 1


@pytest.mark.django_db
def test_officer_can_delete_unpublished_intake(facility, officer):
    from register_intake.models import Intake

    c = client_for(officer)
    payload = {
        "facility": str(facility.id),
        "register_family": "ANC",
        "batch_period_from": "2026-01-01",
        "batch_period_to": "2026-01-31",
    }
    created = c.post("/api/v1/intakes", {**payload, "images": _img(content=b"del")}, format="multipart")
    intake_id = created.json()["id"]
    deleted = c.delete(f"/api/v1/intakes/{intake_id}")
    assert deleted.status_code == 204
    assert not Intake.objects.filter(id=intake_id).exists()


@pytest.mark.django_db
def test_published_intake_cannot_be_deleted(facility, officer):
    from register_intake.models import Intake, IntakeStatus

    c = client_for(officer)
    payload = {
        "facility": str(facility.id),
        "register_family": "ANC",
        "batch_period_from": "2026-01-01",
        "batch_period_to": "2026-01-31",
    }
    created = c.post("/api/v1/intakes", {**payload, "images": _img(content=b"pub")}, format="multipart")
    intake_id = created.json()["id"]
    Intake.objects.filter(id=intake_id).update(status=IntakeStatus.PUBLISHED)
    blocked = c.delete(f"/api/v1/intakes/{intake_id}")
    assert blocked.status_code == 409
    assert Intake.objects.filter(id=intake_id).exists()  # still there


@pytest.mark.django_db
def test_officer_cannot_delete_another_officers_intake(facility, officer):
    from register_intake.models import Intake

    other = User.objects.create_user(email="other-do@x.com", name="Other DO", role=Role.DATA_OFFICER)
    c_owner = client_for(officer)
    created = c_owner.post(
        "/api/v1/intakes",
        {
            "facility": str(facility.id),
            "register_family": "ANC",
            "batch_period_from": "2026-01-01",
            "batch_period_to": "2026-01-31",
            "images": _img(content=b"mine"),
        },
        format="multipart",
    )
    intake_id = created.json()["id"]
    denied = client_for(other).delete(f"/api/v1/intakes/{intake_id}")
    assert denied.status_code == 404  # not visible to a different officer
    assert Intake.objects.filter(id=intake_id).exists()


@pytest.mark.django_db
def test_organisation_user_cannot_create_intake(facility):
    from identity_access.models import Organisation

    org = Organisation.objects.create(name="NGO")
    org_user = User.objects.create_user(
        email="o@ngo.org", name="Org", role=Role.ORGANISATION_USER, organisation=org
    )
    c = client_for(org_user)
    r = c.post(
        "/api/v1/intakes",
        {"facility": str(facility.id), "register_family": "ANC",
         "batch_period_from": "2026-01-01", "batch_period_to": "2026-01-31", "images": _img()},
        format="multipart",
    )
    assert r.status_code == 403
