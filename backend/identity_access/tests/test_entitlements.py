"""Intelligence module entitlements (11-intelligence-module.md).

Verifies the server-side gate: tiers bundle modules, organisations may add
individual add-on modules, a facility lead sees everything for their own
facility, and an endpoint whose module is not entitled is rejected regardless of
the sidebar — enforcement lives on the API, never in the UI.
"""
import pytest
from rest_framework.test import APIClient

from identity_access import auth_service
from identity_access.entitlements import entitled_modules, module_for_path
from identity_access.models import (
    Facility,
    LocalGovernment,
    Organisation,
    Role,
    State,
    SubscriptionTier,
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
def essentials(db):
    # A tier with a KNOWN composition, independent of whatever the seed/rebalance
    # migrations ship, so these entitlement assertions stay deterministic.
    tier, _ = SubscriptionTier.objects.update_or_create(
        slug="essentials",
        defaults={"name": "Essentials", "modules": ["overview", "care_journey", "reports"], "order": 1},
    )
    return tier


@pytest.mark.django_db
def test_facility_lead_sees_every_module(facility):
    lead = User.objects.create_user(email="lead@x.com", name="Lead", role=Role.FACILITY_LEAD, facility=facility)
    mods = entitled_modules(lead)
    assert "surveillance" in mods and "records" in mods and "overview" in mods


@pytest.mark.django_db
def test_tier_bundles_modules(essentials):
    org = Organisation.objects.create(name="NGO", tier=essentials)
    user = User.objects.create_user(email="o@ngo.org", name="Org", role=Role.ORGANISATION_USER, organisation=org)
    mods = entitled_modules(user)
    assert mods == {"overview", "care_journey", "reports"}


@pytest.mark.django_db
def test_add_on_module_extends_tier(essentials):
    org = Organisation.objects.create(name="NGO", tier=essentials, extra_modules=["benchmarking"])
    user = User.objects.create_user(email="o@ngo.org", name="Org", role=Role.ORGANISATION_USER, organisation=org)
    assert entitled_modules(user) == {"overview", "care_journey", "reports", "benchmarking"}


@pytest.mark.django_db
def test_org_with_no_tier_has_nothing():
    org = Organisation.objects.create(name="NGO")
    user = User.objects.create_user(email="o@ngo.org", name="Org", role=Role.ORGANISATION_USER, organisation=org)
    assert entitled_modules(user) == set()


@pytest.mark.django_db
def test_endpoint_rejected_when_module_not_entitled(essentials):
    """Essentials excludes surveillance — the deaths & stillbirths API is 403."""
    org = Organisation.objects.create(name="NGO", tier=essentials)
    user = User.objects.create_user(email="o@ngo.org", name="Org", role=Role.ORGANISATION_USER, organisation=org)
    c = client_for(user)
    # Entitled module responds (200); non-entitled is blocked (403).
    assert c.get("/api/v1/surveillance/cases").status_code == 403
    assert c.get("/api/v1/reports").status_code == 200


@pytest.mark.django_db
def test_add_on_opens_the_endpoint(essentials):
    org = Organisation.objects.create(name="NGO", tier=essentials, extra_modules=["surveillance"])
    user = User.objects.create_user(email="o@ngo.org", name="Org", role=Role.ORGANISATION_USER, organisation=org)
    assert client_for(user).get("/api/v1/surveillance/cases").status_code == 200


@pytest.mark.django_db
def test_self_serializer_exposes_entitled_modules(essentials):
    org = Organisation.objects.create(name="NGO", tier=essentials)
    user = User.objects.create_user(email="o@ngo.org", name="Org", role=Role.ORGANISATION_USER, organisation=org)
    body = client_for(user).get("/api/v1/users/me").json()
    assert set(body["entitled_modules"]) == {"overview", "care_journey", "reports"}


def test_path_mapping():
    assert module_for_path("/api/v1/surveillance/summary") == "surveillance"
    assert module_for_path("/api/v1/benchmarking") == "benchmarking"
    assert module_for_path("/api/v1/geo") == "benchmarking"
    assert module_for_path("/api/v1/reports") == "reports"
    assert module_for_path("/api/v1/workspace") is None
