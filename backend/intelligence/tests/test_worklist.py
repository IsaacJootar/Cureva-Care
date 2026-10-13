"""Worklist rule engine + access control (cureva-docs/05, 06)."""
import datetime

import pytest
from rest_framework.test import APIClient

from identity_access import auth_service
from identity_access.models import Facility, LocalGovernment, Organisation, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from intelligence.models import WorklistAction
from intelligence.rules import evaluate_worklist
from maternal_projection.models import ANCContact, PregnancyEpisode, Woman


@pytest.fixture
def facility(db):
    state = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=state, name="Nassarawa")
    ward = Ward.objects.create(local_government=lga, name="Gama")
    return Facility.objects.create(ward=ward, name="Gama PHC")


def _anc_contact(facility, bp=None, hb=None):
    officer = User.objects.create_user(email=f"do{Woman.objects.count()}@x.com", name="DO", role=Role.DATA_OFFICER)
    woman = Woman.objects.create(facility=facility, name="Amina", stable_identifier=f"A{ANCContact.objects.count()}")
    ep = PregnancyEpisode.objects.create(woman=woman, facility=facility)
    intake = Intake.objects.create(
        facility=facility, submitted_by=officer, register_family="ANC", source_hash=f"h{ANCContact.objects.count()}",
        batch_period_from=datetime.date(2026, 1, 1), batch_period_to=datetime.date(2026, 1, 31),
    )
    row = SourceRow.objects.create(intake=intake, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})
    data = {}
    if bp:
        data["blood_pressure"] = bp
    if hb:
        data["haemoglobin"] = hb
    return ANCContact.objects.create(episode=ep, woman=woman, facility=facility, source_row=row, data=data, service_date=datetime.date(2026, 1, 10))


@pytest.mark.django_db
def test_abnormal_bp_and_anaemia_raise_worklist_items(facility):
    _anc_contact(facility, bp="160/100")
    _anc_contact(facility, hb="8.5")
    items = evaluate_worklist([facility.id])
    keys = {i["rule_key"] for i in items}
    assert "abnormal_bp" in keys
    assert "anaemia" in keys
    # High severity sorts first.
    assert items[0]["severity"] == "high"


@pytest.mark.django_db
def test_normal_values_raise_nothing(facility):
    _anc_contact(facility, bp="120/80", hb="12.5")
    assert evaluate_worklist([facility.id]) == []


def _client(user):
    c = APIClient()
    raw = auth_service.mint_signin_ticket(user)
    access = c.post("/api/v1/auth/session", {"token": raw}, format="json").json()["access"]
    c.credentials(HTTP_AUTHORIZATION="Bearer " + access)
    return c


@pytest.mark.django_db
def test_worklist_is_facility_lead_only(facility):
    _anc_contact(facility, bp="150/95")
    lead = User.objects.create_user(email="lead@x.com", name="Lead", role=Role.FACILITY_LEAD, facility=facility)
    org = Organisation.objects.create(name="NGO")
    org_user = User.objects.create_user(email="o@ngo.org", name="Org", role=Role.ORGANISATION_USER, organisation=org)

    # Facility lead can read the worklist.
    r = _client(lead).get("/api/v1/worklists")
    assert r.status_code == 200
    assert len(r.json()["items"]) >= 1

    # Organisation user is rejected outright (read restriction, not a filter).
    assert _client(org_user).get("/api/v1/worklists").status_code == 403


@pytest.mark.django_db
def test_action_is_overlay_and_item_resurfaces(facility):
    c = _anc_contact(facility, bp="160/100")
    lead = User.objects.create_user(email="lead2@x.com", name="Lead", role=Role.FACILITY_LEAD, facility=facility)
    client = _client(lead)
    items = client.get("/api/v1/worklists").json()["items"]
    item = items[0]

    resp = client.post(
        f"/api/v1/worklists/{item['item_id']}/action",
        {"note": "Called the patient", "subject_type": item["subject_type"]},
        format="json",
    )
    assert resp.status_code == 201
    assert WorklistAction.objects.count() == 1

    # The item is NOT removed — it resurfaces (still true) now with action history.
    items2 = client.get("/api/v1/worklists").json()["items"]
    same = next(i for i in items2 if i["item_id"] == item["item_id"])
    assert same["last_actioned"]["by"] == "Lead"
    assert same["last_actioned"]["note"] == "Called the patient"
