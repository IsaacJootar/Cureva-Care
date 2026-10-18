"""Email + password authentication (replaces Google SSO)."""
import pytest
from rest_framework.test import APIClient

from identity_access import auth_service
from identity_access.models import Role, User


@pytest.fixture
def api():
    return APIClient()


@pytest.mark.django_db
def test_password_login_succeeds_and_rejects_wrong(api):
    User.objects.create_user(email="lead@x.com", name="Lead", role=Role.FACILITY_LEAD, password="s3cretpass")
    ok = api.post("/api/v1/auth/login", {"email": "lead@x.com", "password": "s3cretpass"}, format="json")
    assert ok.status_code == 200
    assert "access" in ok.json()
    bad = api.post("/api/v1/auth/login", {"email": "lead@x.com", "password": "wrong"}, format="json")
    assert bad.status_code == 401


@pytest.mark.django_db
def test_login_rejects_user_without_password(api):
    # A user created without a password (unusable) cannot log in by password.
    User.objects.create_user(email="np@x.com", name="NoPass", role=Role.FACILITY_LEAD)
    r = api.post("/api/v1/auth/login", {"email": "np@x.com", "password": "anything"}, format="json")
    assert r.status_code == 401


@pytest.mark.django_db
def test_inactive_user_cannot_log_in(api):
    u = User.objects.create_user(email="x@x.com", name="X", role=Role.FACILITY_LEAD, password="s3cretpass")
    u.is_active = False
    u.save(update_fields=["is_active"])
    r = api.post("/api/v1/auth/login", {"email": "x@x.com", "password": "s3cretpass"}, format="json")
    assert r.status_code == 401


@pytest.mark.django_db
def test_change_password(api):
    u = User.objects.create_user(email="c@x.com", name="C", role=Role.FACILITY_LEAD, password="oldpass12")
    raw = auth_service.mint_signin_ticket(u)
    access = api.post("/api/v1/auth/session", {"token": raw}, format="json").json()["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    r = api.post("/api/v1/auth/change-password", {"current_password": "oldpass12", "new_password": "newpass12"}, format="json")
    assert r.status_code == 200
    u.refresh_from_db()
    assert u.check_password("newpass12")


@pytest.mark.django_db
def test_admin_create_user_generates_shareable_password(api):
    admin = User.objects.create_user(email="admin@x.com", name="Admin", role=Role.SYSTEMS_ADMIN, password="adminpass1")
    raw = auth_service.mint_signin_ticket(admin)
    access = api.post("/api/v1/auth/session", {"token": raw}, format="json").json()["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    r = api.post("/api/v1/users", {"name": "New Officer", "email": "new@x.com", "role": "data_officer"}, format="json")
    assert r.status_code == 201
    pw = r.json()["initial_password"]
    assert pw and pw.startswith("Cureva-")
    # The generated password actually works.
    login = api.post("/api/v1/auth/login", {"email": "new@x.com", "password": pw}, format="json")
    assert login.status_code == 200
