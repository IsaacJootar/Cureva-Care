"""Comprehensive access-control suite (cureva-docs/07, launch gates).

Verifies the server-side boundaries, not just UI hiding: organisation users are
read-only at the API, the org-user-delete exception is narrow, settings are
admin-only, and notification preferences are self-only.
"""
import pytest
from rest_framework.test import APIClient

from identity_access import auth_service
from identity_access.models import (
    Facility,
    LocalGovernment,
    Organisation,
    Role,
    State,
    User,
    Ward,
)


@pytest.fixture
def facility(db):
    s = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=s, name="Nassarawa")
    w = Ward.objects.create(local_government=lga, name="Gama")
    return Facility.objects.create(ward=w, name="Gama PHC")


def client_for(user):
    c = APIClient()
    raw = auth_service.mint_signin_ticket(user)
    access = c.post("/api/v1/auth/session", {"token": raw}, format="json").json()["access"]
    c.credentials(HTTP_AUTHORIZATION="Bearer " + access)
    return c


@pytest.fixture
def admin(db):
    return User.objects.create_user(email="admin@x.com", name="Admin", role=Role.SYSTEMS_ADMIN)


@pytest.mark.django_db
def test_settings_are_admin_only(admin, facility):
    do = User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)
    assert client_for(admin).get("/api/v1/settings").status_code == 200
    assert client_for(do).get("/api/v1/settings").status_code == 403


@pytest.mark.django_db
def test_setting_update_validates_type(admin):
    r = client_for(admin).patch("/api/v1/settings/stale_facility_alert_days", {"value": "notanumber"}, format="json")
    assert r.status_code == 400
    ok = client_for(admin).patch("/api/v1/settings/stale_facility_alert_days", {"value": 21}, format="json")
    assert ok.status_code == 200 and ok.json()["value"] == 21


@pytest.mark.django_db
def test_capture_endpoints_reject_organisation_users(facility):
    org = Organisation.objects.create(name="NGO")
    org_user = User.objects.create_user(email="o@ngo.org", name="Org", role=Role.ORGANISATION_USER, organisation=org)
    c = client_for(org_user)
    # Intake creation, template creation, settings, user creation — all rejected.
    assert c.post("/api/v1/intakes", {}, format="multipart").status_code == 403
    assert c.post("/api/v1/templates", {}, format="json").status_code == 403
    assert c.get("/api/v1/settings").status_code == 403
    assert c.post("/api/v1/users", {}, format="json").status_code == 403
    assert c.get("/api/v1/worklists").status_code == 403


@pytest.mark.django_db
def test_org_user_delete_exception_is_narrow():
    org_a = Organisation.objects.create(name="A")
    org_b = Organisation.objects.create(name="B")
    manager = User.objects.create_user(email="mgr@a.org", name="Mgr", role=Role.ORGANISATION_USER, organisation=org_a, can_manage_org_users=True)
    colleague = User.objects.create_user(email="c@a.org", name="Colleague", role=Role.ORGANISATION_USER, organisation=org_a)
    other = User.objects.create_user(email="x@b.org", name="Other", role=Role.ORGANISATION_USER, organisation=org_b)
    plain = User.objects.create_user(email="p@a.org", name="Plain", role=Role.ORGANISATION_USER, organisation=org_a, can_manage_org_users=False)

    mgr_client = client_for(manager)
    # Can deactivate own-org colleague.
    assert mgr_client.delete(f"/api/v1/organisations/{org_a.id}/users/{colleague.id}").status_code == 204
    # Cannot touch another org's user.
    assert mgr_client.delete(f"/api/v1/organisations/{org_b.id}/users/{other.id}").status_code == 403
    # A plain org user (no manage flag) cannot delete anyone.
    assert client_for(plain).delete(f"/api/v1/organisations/{org_a.id}/users/{manager.id}").status_code == 403


@pytest.mark.django_db
def test_notification_preferences_are_self_only(facility):
    lead = User.objects.create_user(email="lead@x.com", name="Lead", role=Role.FACILITY_LEAD, facility=facility)
    other = User.objects.create_user(email="lead2@x.com", name="Lead2", role=Role.FACILITY_LEAD, facility=facility)
    c = client_for(lead)
    assert c.get(f"/api/v1/users/{lead.id}/notification-preferences").status_code == 200
    assert c.get(f"/api/v1/users/{other.id}/notification-preferences").status_code == 403
    # Self can change own channel.
    r = c.patch(f"/api/v1/users/{lead.id}/notification-preferences/stale_facility_alert", {"channel": "sms"}, format="json")
    assert r.status_code == 200 and r.json()["channel"] == "sms"


@pytest.mark.django_db
def test_admin_can_edit_and_deactivate_user(admin, facility):
    target = User.objects.create_user(email="t@x.com", name="Target", role=Role.DATA_OFFICER)
    c = client_for(admin)
    assert c.patch(f"/api/v1/users/{target.id}", {"name": "Renamed"}, format="json").status_code == 200
    assert c.post(f"/api/v1/users/{target.id}/deactivate").status_code == 200
    target.refresh_from_db()
    assert target.is_active is False and target.name == "Renamed"
    assert c.post(f"/api/v1/users/{target.id}/reactivate").status_code == 200
