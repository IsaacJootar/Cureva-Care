"""Continuum & cohort engine (WS3)."""
import datetime

import pytest

from identity_access.models import AccessLevel, Facility, LocalGovernment, Role, State, User, Ward
from register_intake.models import Intake, SourceRow
from maternal_projection.models import ANCContact, BirthEvent, PNCContact, PregnancyEpisode, Woman
from intelligence.continuum import care_funnel, cohort_retention, dropoff_lines

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


def _intake(facility, officer, fam):
    return Intake.objects.create(
        facility=facility, submitted_by=officer, register_family=fam, source_hash=f"h{Intake.objects.count()}",
        batch_period_from=D(2026, 1, 1), batch_period_to=D(2026, 3, 31),
    )


def _row(intake):
    return SourceRow.objects.create(intake=intake, row_number=1, raw_payload={}, normalized={}, status="verified", extraction_confidence={})


def _woman(facility, name):
    return Woman.objects.create(facility=facility, name=name, stable_identifier=f"S{Woman.objects.count()}")


def _episode(woman, facility, booking=D(2026, 1, 5)):
    return PregnancyEpisode.objects.create(woman=woman, facility=facility, booking_date=booking)


def _build(facility, officer):
    # Woman A: 4 ANC + delivery + PNC → completes the funnel.
    a = _woman(facility, "Amina"); epa = _episode(a, facility)
    for i in range(4):
        ANCContact.objects.create(episode=epa, woman=a, facility=facility, source_row=_row(_intake(facility, officer, "ANC")), data={}, service_date=D(2026, 1, 10 + i))
    BirthEvent.objects.create(episode=epa, woman=a, facility=facility, source_row=_row(_intake(facility, officer, "Delivery")), data={}, delivery_date=D(2026, 6, 1), still_birth=False)
    PNCContact.objects.create(episode=epa, woman=a, facility=facility, source_row=_row(_intake(facility, officer, "PNC")), data={}, visit_date=D(2026, 6, 3))
    # Woman B: 2 ANC, no delivery → anc_under_4 + booked_no_delivery.
    b = _woman(facility, "Bisi"); epb = _episode(b, facility)
    for i in range(2):
        ANCContact.objects.create(episode=epb, woman=b, facility=facility, source_row=_row(_intake(facility, officer, "ANC")), data={}, service_date=D(2026, 2, 1 + i))
    # Woman C: delivered, no PNC → delivered_no_pnc.
    c = _woman(facility, "Chiamaka"); epc = _episode(c, facility)
    BirthEvent.objects.create(episode=epc, woman=c, facility=facility, source_row=_row(_intake(facility, officer, "Delivery")), data={}, delivery_date=D(2026, 7, 1), still_birth=False)
    return a, b, c


@pytest.mark.django_db
def test_funnel_counts(facility, officer):
    _build(facility, officer)
    f = care_funnel([facility.id])
    steps = {s["label"]: s["value"] for s in f["steps"]}
    assert steps["Booked"] == 3
    assert steps["4+ ANC contacts"] == 1  # only Amina
    assert steps["Delivered"] == 2        # Amina + Chiamaka
    assert steps["Postnatal contact"] == 1  # only Amina


@pytest.mark.django_db
def test_dropoff_delivered_no_pnc_lists_named_woman(facility, officer):
    _build(facility, officer)
    d = dropoff_lines([facility.id], "delivered_no_pnc", AccessLevel.IDENTIFIABLE)
    assert d["count"] == 1
    assert d["rows"][0]["woman"]["name"] == "Chiamaka"


@pytest.mark.django_db
def test_dropoff_aggregate_tier_hides_women(facility, officer):
    _build(facility, officer)
    d = dropoff_lines([facility.id], "delivered_no_pnc", AccessLevel.AGGREGATE)
    assert d["count"] == 1
    assert d["rows"] == []  # counts only


@pytest.mark.django_db
def test_dropoff_de_identified_strips_name(facility, officer):
    _build(facility, officer)
    d = dropoff_lines([facility.id], "anc_under_4", AccessLevel.DE_IDENTIFIED)
    assert d["count"] == 1
    assert d["rows"][0]["woman"] is None


@pytest.mark.django_db
def test_cohort_retention_buckets_by_booking_month(facility, officer):
    _build(facility, officer)
    c = cohort_retention([facility.id])
    assert "2026-01" in c["cohorts"]
    # Jan cohort: Amina + Bisi + Chiamaka all booked 2026-01-05.
    jan = {p["x"]: p for p in c["series"]["anc4"]["points"]}
    assert jan["2026-01"]["denominator"] == 3
    assert jan["2026-01"]["numerator"] == 1  # only Amina reached 4+
