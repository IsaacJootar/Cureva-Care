"""Metric reconciliation — the Module 4 exit condition.

Publishes a known fixture through the real pipeline (extract -> project ->
aggregate -> metrics) and checks the dashboard numbers reconcile exactly with
hand-calculated values, including that an organisation scoped to a subset of
facilities sees exactly that subset — no more, no less.
"""
import datetime
import uuid

import pytest

from identity_access.models import (
    AccessLevel,
    Facility,
    LocalGovernment,
    Organisation,
    OrganisationFacilityAccess,
    Role,
    ScopeType,
    State,
    User,
    Ward,
)
from register_intake.extraction import MockExtractor
from register_intake.models import Intake
from register_intake.pipeline import process_intake, row_needs_confirmation
from register_intake.publish import confirm_field, publish_intake
from identity_access.services import get_setting
from identity_access.settings_registry import AI_EXTRACTION_CONFIDENCE_THRESHOLD
from intelligence.metrics import maternal_summary
from intelligence.scoping import resolve_org_facility_ids
from maternal_projection.models import ANCContact, BirthEvent, PNCContact, Woman


@pytest.fixture
def world(db):
    state = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=state, name="Nassarawa")
    ward = Ward.objects.create(local_government=lga, name="Gama")
    fac_a = Facility.objects.create(ward=ward, name="Facility A")
    fac_b = Facility.objects.create(ward=ward, name="Facility B")
    officer = User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)
    return {"a": fac_a, "b": fac_b, "officer": officer}


def pub(facility, officer, family, fields):
    conf = {k: 0.99 for k in fields}
    intake = Intake.objects.create(
        facility=facility, submitted_by=officer, register_family=family,
        source_hash=uuid.uuid4().hex,
        batch_period_from=datetime.date(2026, 3, 1), batch_period_to=datetime.date(2026, 3, 31),
    )
    process_intake(intake, [b"x"], MockExtractor([{"fields": fields, "confidence": conf}]))
    # Confirm every field still needing confirmation (incl. always-confirm
    # identity fields like card_number), then publish.
    threshold = float(get_setting(AI_EXTRACTION_CONFIDENCE_THRESHOLD))
    for row in intake.rows.all():
        for f in row_needs_confirmation(row, threshold):
            confirm_field(row, f, None, officer, correct=False)
    publish_intake(intake, officer)
    return intake


@pytest.mark.django_db
def test_metrics_reconcile_and_org_scopes_to_granted_facilities(world):
    a, b, officer = world["a"], world["b"], world["officer"]

    # --- Facility A: one woman (card A1) across ANC x2, Delivery, PNC ---
    pub(a, officer, "ANC", {"Card No": "A1", "LMP": "2026-01-01", "Gestational Age": "10", "Gravida": "2", "Parity": "1", "HIV": "Negative", "Iron & Folate": "Yes"})
    pub(a, officer, "ANC", {"Card No": "A1", "LMP": "2026-01-01", "Gestational Age": "16", "Gravida": "2", "Parity": "1"})
    pub(a, officer, "Delivery", {"Card No": "A1", "Date of Delivery": "2026-03-10", "Mode of Delivery": "SVD", "Birth Weight": "3.2", "Stillbirth": "No", "Birth Attendant": "Midwife"})
    pub(a, officer, "PNC", {"Card No": "A1", "Visit Date": "2026-03-13", "Days Postpartum": "3", "Subject": "mother", "Feeding": "Exclusive", "Danger Signs": "None", "Referral": "Referred to GH"})

    # --- Facility B: a different woman, one ANC contact ---
    pub(b, officer, "ANC", {"Card No": "B1", "LMP": "2026-02-01", "Gestational Age": "9", "Gravida": "1", "Parity": "0"})

    # One woman per facility (strict identifier).
    assert Woman.objects.filter(facility=a).count() == 1
    assert Woman.objects.filter(facility=b).count() == 1

    # Facility A projected events reconcile.
    assert ANCContact.objects.filter(facility=a).count() == 2
    assert BirthEvent.objects.filter(facility=a).count() == 1
    assert PNCContact.objects.filter(facility=a).count() == 1

    summ_a = maternal_summary([a.id])
    assert summ_a["operational"]["anc_contacts"] == 2
    assert summ_a["operational"]["deliveries"] == 1
    assert summ_a["operational"]["pnc_contacts"] == 1
    assert summ_a["operational"]["verified_records"] == 4
    assert summ_a["operational"]["open_referrals"] == 1  # the PNC referral
    # Early booking: the episode's booking GA is 10 wks (<=12) -> 1/1.
    assert summ_a["metrics"]["early_anc_booking"] == {"numerator": 1, "denominator": 1, "rate": 1.0}
    # Delivery linkage: the one birth's episode has ANC contacts -> 1/1.
    assert summ_a["care_journey"]["delivery_linkage"]["rate"] == 1.0
    # Postnatal linkage: the birth episode has a PNC contact -> 1/1.
    assert summ_a["care_journey"]["postnatal_linkage"]["rate"] == 1.0
    assert summ_a["outcomes"]["live_births"] == 1
    assert summ_a["outcomes"]["still_births"] == 0

    # --- Organisation granted ONLY facility A sees exactly A's numbers ---
    admin = User.objects.create_user(email="admin@x.com", name="Admin", role=Role.SYSTEMS_ADMIN)
    org = Organisation.objects.create(name="NGO")
    OrganisationFacilityAccess.objects.create(
        organisation=org, scope_type=ScopeType.FACILITY, scope_id=a.id,
        access_level=AccessLevel.AGGREGATE, granted_by=admin,
    )
    org_facilities = resolve_org_facility_ids(org.id)
    assert org_facilities == {a.id}  # not B

    summ_org = maternal_summary(org_facilities)
    assert summ_org["operational"]["anc_contacts"] == 2  # A only, B's 1 excluded
    assert summ_org["operational"]["verified_records"] == 4

    # Whole picture (A + B) differs from A alone — proves scoping matters.
    summ_all = maternal_summary([a.id, b.id])
    assert summ_all["operational"]["anc_contacts"] == 3


@pytest.mark.django_db
def test_region_grant_expands_to_facilities(world):
    a, b = world["a"], world["b"]
    admin = User.objects.create_user(email="admin2@x.com", name="Admin", role=Role.SYSTEMS_ADMIN)
    org = Organisation.objects.create(name="Gov")
    # Grant the whole ward — both facilities are under it.
    OrganisationFacilityAccess.objects.create(
        organisation=org, scope_type=ScopeType.WARD, scope_id=a.ward_id,
        access_level=AccessLevel.AGGREGATE, granted_by=admin,
    )
    assert resolve_org_facility_ids(org.id) == {a.id, b.id}
