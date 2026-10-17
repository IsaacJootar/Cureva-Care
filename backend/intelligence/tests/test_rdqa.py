"""RDQA-as-a-service (WS6)."""
import datetime

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from intelligence.rdqa import rdqa_scorecard

D = datetime.date


@pytest.fixture
def facility(db):
    s = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=s, name="Nassarawa")
    w = Ward.objects.create(local_government=lga, name="Gama")
    return Facility.objects.create(ward=w, name="Gama PHC")


@pytest.fixture
def officer(db):
    return User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)


@pytest.mark.django_db
def test_scorecard_reports_confidence_and_score(facility, officer):
    intake = Intake.objects.create(
        facility=facility, submitted_by=officer, register_family="ANC", source_hash="h1",
        batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 1, 31),
    )
    SourceRow.objects.create(
        intake=intake, row_number=1, raw_payload={}, normalized={"lmp": "2026-01-01", "gravida": 2},
        status="verified", extraction_confidence={"lmp": 0.98, "gravida": 0.96},
    )
    SourceRow.objects.create(
        intake=intake, row_number=2, raw_payload={}, normalized={"lmp": "2026-01-02"},
        status="verified", extraction_confidence={"lmp": 0.9},
        flags={"gestational_age_weeks": {"kind": "implausible", "message": "x"}},
    )
    sc = rdqa_scorecard([facility.id])
    assert sc["overall"]["facilities_assessed"] == 1
    card = sc["facilities"][0]
    assert card["rows"] == 2
    assert card["avg_extraction_confidence"] is not None and card["avg_extraction_confidence"] > 0.9
    assert card["implausible_rate"] == 0.5  # one of two rows flagged
    assert card["score"] is not None


@pytest.mark.django_db
def test_empty_scope():
    assert rdqa_scorecard([]) == {"facilities": [], "overall": {}}
