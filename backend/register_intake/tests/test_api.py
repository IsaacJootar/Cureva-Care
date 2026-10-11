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
    row_id = rows[0]["id"]

    # Publish blocked until the low-confidence field is confirmed.
    blocked = c.post(f"/api/v1/intakes/{intake_id}/publish")
    assert blocked.status_code == 409

    c.post(
        f"/api/v1/intakes/{intake_id}/rows/{row_id}/confirm-field",
        {"field": "gravida", "correct": False},
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
