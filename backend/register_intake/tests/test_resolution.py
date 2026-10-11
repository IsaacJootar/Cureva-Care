"""Template resolution + source fingerprinting (cureva-docs/03)."""
import datetime

import pytest

from identity_access.models import Facility, LocalGovernment, State, Ward
from register_intake.models import Template
from register_intake.resolution import (
    NoTemplateRegistered,
    compute_source_hash,
    resolve_template,
)


@pytest.fixture
def facility(db):
    state = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=state, name="Nassarawa")
    ward = Ward.objects.create(local_government=lga, name="Gama")
    return Facility.objects.create(ward=ward, name="Gama PHC")


@pytest.mark.django_db
def test_resolves_shared_default_when_no_facility_template(facility):
    t = resolve_template("ANC", facility.id)
    assert t.facility_id is None  # the seeded shared default
    assert t.register_family == "ANC"


@pytest.mark.django_db
def test_facility_specific_template_wins_over_shared(facility):
    facility_tpl = Template.objects.create(
        register_family="ANC",
        facility=facility,
        version=1,
        effective_date=datetime.date(2026, 1, 1),
        is_active=True,
        schema={"register_family": "ANC", "version": 1, "columns": []},
    )
    t = resolve_template("ANC", facility.id)
    assert t.id == facility_tpl.id


@pytest.mark.django_db
def test_raises_when_no_template_at_all(facility):
    Template.objects.filter(register_family="ANC").delete()
    with pytest.raises(NoTemplateRegistered):
        resolve_template("ANC", facility.id)


def test_source_hash_is_stable_and_order_independent():
    a, b = b"page-one-bytes", b"page-two-bytes"
    assert compute_source_hash([a, b]) == compute_source_hash([b, a])
    assert compute_source_hash([a, b]) != compute_source_hash([a, a])
