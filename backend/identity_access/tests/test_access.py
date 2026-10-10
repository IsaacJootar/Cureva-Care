"""Role-based access-control tests for the Identity & Access endpoints."""
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


def auth_client(user):
    c = APIClient()
    raw = auth_service.mint_signin_ticket(user)
    access = c.post("/api/v1/auth/session", {"token": raw}, format="json").json()["access"]
    c.credentials(HTTP_AUTHORIZATION="Bearer " + access)
    return c


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        email="admin@example.com", name="Admin", role=Role.SYSTEMS_ADMIN
    )


@pytest.fixture
def ward(db):
    state = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=state, name="Nassarawa")
    return Ward.objects.create(local_government=lga, name="Gama")


@pytest.mark.django_db
def test_facility_create_is_admin_only(admin, ward):
    facility_lead = User.objects.create_user(
        email="lead@example.com", name="Lead", role=Role.FACILITY_LEAD,
        facility=Facility.objects.create(ward=ward, name="Seed PHC"),
    )
    payload = {"name": "New PHC", "ward": str(ward.id)}

    # Admin can.
    r = auth_client(admin).post("/api/v1/facilities", payload, format="json")
    assert r.status_code == 201

    # Facility lead cannot.
    r = auth_client(facility_lead).post("/api/v1/facilities", payload, format="json")
    assert r.status_code == 403


@pytest.mark.django_db
def test_facility_requires_ward(admin):
    r = auth_client(admin).post("/api/v1/facilities", {"name": "Wardless"}, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
def test_organisation_management_is_admin_only(admin):
    data_officer = User.objects.create_user(
        email="do@example.com", name="DO", role=Role.DATA_OFFICER
    )
    assert auth_client(admin).get("/api/v1/organisations").status_code == 200
    assert auth_client(data_officer).get("/api/v1/organisations").status_code == 403


@pytest.mark.django_db
def test_admin_creates_org_and_grants_facility_access(admin, ward):
    facility = Facility.objects.create(ward=ward, name="Grantable PHC")
    c = auth_client(admin)
    org = c.post("/api/v1/organisations", {"name": "Donor NGO", "org_type": "NGO"}, format="json")
    assert org.status_code == 201
    org_id = org.json()["id"]

    grant = c.post(
        f"/api/v1/organisations/{org_id}/facility-access",
        {"scope_type": "facility", "scope_id": str(facility.id), "access_level": "aggregate"},
        format="json",
    )
    assert grant.status_code == 201
    assert grant.json()["access_level"] == "aggregate"  # least-identifiable default tier


@pytest.mark.django_db
def test_org_user_without_manage_flag_cannot_list_org_users(admin):
    org = Organisation.objects.create(name="NGO")
    member = User.objects.create_user(
        email="m@ngo.org", name="Member", role=Role.ORGANISATION_USER,
        organisation=org, can_manage_org_users=False,
    )
    r = auth_client(member).get(f"/api/v1/organisations/{org.id}/users")
    assert r.status_code == 403


@pytest.mark.django_db
def test_org_manager_can_invite_only_into_own_org(admin):
    org_a = Organisation.objects.create(name="A")
    org_b = Organisation.objects.create(name="B")
    manager = User.objects.create_user(
        email="mgr@a.org", name="Mgr", role=Role.ORGANISATION_USER,
        organisation=org_a, can_manage_org_users=True,
    )
    c = auth_client(manager)

    # Into own org: allowed, always role organisation_user.
    r = c.post(
        f"/api/v1/organisations/{org_a.id}/users",
        {"name": "Colleague", "email": "c@a.org"}, format="json",
    )
    assert r.status_code == 201
    assert r.json()["role"] == Role.ORGANISATION_USER

    # Into another org: rejected.
    r = c.post(
        f"/api/v1/organisations/{org_b.id}/users",
        {"name": "Intruder", "email": "x@b.org"}, format="json",
    )
    assert r.status_code == 403


@pytest.mark.django_db
def test_user_cannot_have_both_facility_and_organisation():
    from django.db import IntegrityError

    org = Organisation.objects.create(name="NGO")
    state = State.objects.create(name="Lagos")
    lga = LocalGovernment.objects.create(state=state, name="Ikeja")
    ward = Ward.objects.create(local_government=lga, name="Ward 1")
    facility = Facility.objects.create(ward=ward, name="PHC")
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            email="bad@example.com", name="Bad", role=Role.FACILITY_LEAD,
            facility=facility, organisation=org,
        )
