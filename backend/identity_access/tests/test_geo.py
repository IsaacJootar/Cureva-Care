"""Geo hierarchy: picker chain + the authentic seed command."""
import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from identity_access import auth_service
from identity_access.models import (
    LocalGovernment,
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


@pytest.mark.django_db
def test_picker_chain_narrows_by_parent(admin):
    kano = State.objects.create(name="Kano")
    lagos = State.objects.create(name="Lagos")
    nassarawa = LocalGovernment.objects.create(state=kano, name="Nassarawa")
    LocalGovernment.objects.create(state=lagos, name="Ikeja")
    gama = Ward.objects.create(local_government=nassarawa, name="Gama")

    c = auth_client(admin)

    states = c.get("/api/v1/states").json()
    assert {s["name"] for s in states} == {"Kano", "Lagos"}

    kano_lgas = c.get(f"/api/v1/states/{kano.id}/local-governments").json()
    assert [l["name"] for l in kano_lgas] == ["Nassarawa"]  # narrowed to Kano only

    wards = c.get(f"/api/v1/local-governments/{nassarawa.id}/wards").json()
    assert [w["name"] for w in wards] == ["Gama"]
    assert wards[0]["id"] == str(gama.id)


@pytest.mark.django_db
def test_seed_geo_loads_ten_states_from_authentic_fixture():
    call_command("seed_geo")
    assert State.objects.count() == 10
    # LGA counts match reality for the pilot states.
    assert LocalGovernment.objects.filter(state__name="Lagos").count() == 20
    assert LocalGovernment.objects.filter(state__name="Kano").count() == 44
    assert State.objects.filter(name="Federal Capital Territory").exists()
    assert Ward.objects.count() > 2000

    # Idempotent.
    call_command("seed_geo")
    assert State.objects.count() == 10
