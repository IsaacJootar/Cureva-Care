"""Auth + session tests: magic-link, single-use tickets, JWT, invite-only."""
import pytest
from rest_framework.test import APIClient

from identity_access import auth_service
from identity_access.models import Role, User


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        email="admin@example.com", name="Admin", role=Role.SYSTEMS_ADMIN
    )


@pytest.mark.django_db
def test_magic_link_request_always_200_even_for_unknown_email(api):
    # Never reveal whether an address is registered.
    r = api.post("/api/v1/auth/magic-link", {"email": "nobody@example.com"}, format="json")
    assert r.status_code == 200


@pytest.mark.django_db
def test_session_exchange_with_valid_ticket_returns_jwt(api, admin):
    raw = auth_service.mint_signin_ticket(admin)
    r = api.post("/api/v1/auth/session", {"token": raw}, format="json")
    assert r.status_code == 200
    body = r.json()
    assert "access" in body and "refresh" in body
    assert body["user"]["role"] == Role.SYSTEMS_ADMIN


@pytest.mark.django_db
def test_signin_ticket_is_single_use(api, admin):
    raw = auth_service.mint_signin_ticket(admin)
    first = api.post("/api/v1/auth/session", {"token": raw}, format="json")
    second = api.post("/api/v1/auth/session", {"token": raw}, format="json")
    assert first.status_code == 200
    assert second.status_code == 400  # already used


@pytest.mark.django_db
def test_inactive_user_cannot_exchange_ticket(api, admin):
    raw = auth_service.mint_signin_ticket(admin)
    admin.is_active = False
    admin.save(update_fields=["is_active"])
    r = api.post("/api/v1/auth/session", {"token": raw}, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
def test_me_requires_auth(api):
    assert api.get("/api/v1/users/me").status_code == 401


@pytest.mark.django_db
def test_me_returns_self_and_rejects_role_change(api, admin):
    raw = auth_service.mint_signin_ticket(admin)
    access = api.post("/api/v1/auth/session", {"token": raw}, format="json").json()["access"]
    api.credentials(HTTP_AUTHORIZATION="Bearer " + access)

    me = api.get("/api/v1/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"

    # Name is editable...
    r = api.patch("/api/v1/users/me", {"name": "Renamed"}, format="json")
    assert r.status_code == 200 and r.json()["name"] == "Renamed"

    # ...role is never self-service.
    r = api.patch("/api/v1/users/me", {"role": Role.DATA_OFFICER}, format="json")
    assert r.status_code == 400
    admin.refresh_from_db()
    assert admin.role == Role.SYSTEMS_ADMIN
