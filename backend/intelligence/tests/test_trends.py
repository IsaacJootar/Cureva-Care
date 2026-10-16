"""Time & trends aggregation (WS1)."""
import datetime

import pytest

from identity_access.models import Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import ANCContact, BirthEvent, PregnancyEpisode, Woman
from intelligence.trends import compute_trends

D = datetime.date


@pytest.fixture
def facility(db):
    state = State.objects.create(name="Kano")
    lga = LocalGovernment.objects.create(state=state, name="Nassarawa")
    ward = Ward.objects.create(local_government=lga, name="Gama")
    return Facility.objects.create(ward=ward, name="Gama PHC")


def _setup(facility):
    officer = User.objects.create_user(email="do@x.com", name="DO", role=Role.DATA_OFFICER)
    woman = Woman.objects.create(facility=facility, name="Amina", stable_identifier="A1")
    ep = PregnancyEpisode.objects.create(woman=woman, facility=facility, booking_date=D(2026, 1, 5), booking_gestational_age_weeks=10)
    intake = Intake.objects.create(
        facility=facility, submitted_by=officer, register_family="ANC", source_hash="h1",
        batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 3, 31),
    )

    def row(n):
        return SourceRow.objects.create(intake=intake, row_number=n, raw_payload={}, normalized={}, status="verified", extraction_confidence={})

    # Two ANC contacts: Jan and Feb; the Feb one has screening recorded.
    ANCContact.objects.create(episode=ep, woman=woman, facility=facility, source_row=row(1), data={}, service_date=D(2026, 1, 10))
    ANCContact.objects.create(episode=ep, woman=woman, facility=facility, source_row=row(2), data={"hiv_result": "NR", "iron_folate_given": True}, service_date=D(2026, 2, 10))
    # A February delivery with a low-birth-weight baby.
    BirthEvent.objects.create(episode=ep, woman=woman, facility=facility, source_row=row(3), data={}, delivery_date=D(2026, 2, 20), still_birth=False, birth_weight_kg=2.1)
    return woman


@pytest.mark.django_db
def test_monthly_buckets_and_counts(facility):
    _setup(facility)
    t = compute_trends([facility.id], bucket="month")
    assert t["bucket"] == "month"
    assert t["buckets"] == ["2026-01", "2026-02"]
    anc = {p["x"]: p["value"] for p in t["metrics"]["anc_contacts"]["points"]}
    assert anc == {"2026-01": 1, "2026-02": 1}
    deliv = {p["x"]: p["value"] for p in t["metrics"]["deliveries"]["points"]}
    assert deliv["2026-02"] == 1
    # Screening coverage: Feb contact has a test, Jan does not.
    screen = {p["x"]: p["rate"] for p in t["metrics"]["screening_coverage"]["points"]}
    assert screen["2026-01"] == 0.0
    assert screen["2026-02"] == 1.0
    # Low birth weight in Feb (2.1 < 2.5).
    lbw = {p["x"]: p["rate"] for p in t["metrics"]["low_birth_weight"]["points"]}
    assert lbw["2026-02"] == 1.0


@pytest.mark.django_db
def test_delta_is_last_vs_previous_bucket(facility):
    _setup(facility)
    t = compute_trends([facility.id], bucket="month")
    # Screening coverage went 0% -> 100% = +100 percentage points.
    assert t["deltas"]["screening_coverage"] == 100


@pytest.mark.django_db
def test_empty_scope_is_empty():
    assert compute_trends([], bucket="month") == {"bucket": "month", "buckets": [], "metrics": {}, "deltas": {}}
