"""Seed a demo organisation that monitors facilities across THREE states, with
realistic (and deliberately different) maternal data in each, so the dashboards
can be explored as a multi-state customer would see them.

Idempotent: re-running won't duplicate the maternal data (guarded by the demo
women already existing). Creates:
  - One facility in each of Kano / Lagos / Rivers (with LGA + ward).
  - Organisation "National Safe Motherhood Initiative" (Enterprise plan) granted
    all three states, de-identified access.
  - Login: multi@cureva.care / Cureva-test1 (organisation user).
  - Coverage population estimates for the three LGAs (2026).

Run: python manage.py seed_multistate_demo
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from identity_access.models import (
    AccessLevel, Facility, LocalGovernment, Organisation, OrganisationFacilityAccess,
    Role, ScopeType, State, SubscriptionTier, User, Ward,
)
from intelligence.models import CoverageDenominator
from maternal_projection.models import ANCContact, BirthEvent, PNCContact, PregnancyEpisode, Woman
from register_intake.models import Intake, SourceRow

# (state, expected_pregnancies, expected_births, profile)
PROFILES = {
    "Kano":   dict(n=18, births=12, still=1, deaths=0, anc4=14, screened=16, early=12, high=1, mod=2, pnc=9,  preg=40, bth=34),
    "Lagos":  dict(n=24, births=18, still=2, deaths=1, anc4=14, screened=15, early=10, high=2, mod=3, pnc=10, preg=60, bth=52),
    "Rivers": dict(n=10, births=5,  still=1, deaths=0, anc4=3,  screened=4,  early=3,  high=1, mod=1, pnc=2,  preg=30, bth=26),
}


class Command(BaseCommand):
    help = "Seed a demo organisation monitoring facilities across three states."

    @transaction.atomic
    def handle(self, *args, **opts):
        officer, _ = User.objects.get_or_create(
            email="officer@cureva.care",
            defaults={"name": "Demo Officer", "role": Role.DATA_OFFICER},
        )
        admin = User.objects.filter(role=Role.SYSTEMS_ADMIN).first() or officer

        facilities = {}
        for state_name, p in PROFILES.items():
            state, _ = State.objects.get_or_create(name=state_name)
            lga, _ = LocalGovernment.objects.get_or_create(state=state, name=f"{state_name} Central")
            ward, _ = Ward.objects.get_or_create(local_government=lga, name=f"{state_name} Ward 1")
            fac, _ = Facility.objects.get_or_create(ward=ward, name=f"{state_name} Demo PHC")
            facilities[state_name] = (state, lga, fac)
            # Coverage population estimate for this LGA (2026).
            CoverageDenominator.objects.update_or_create(
                area_type=CoverageDenominator.AreaType.LOCAL_GOVERNMENT, area_id=lga.id, year=2026,
                defaults={"expected_pregnancies": p["preg"], "expected_births": p["bth"],
                          "source": "WorldPop 2026 (demo)", "updated_by": admin},
            )
            seeded = self._seed_facility(fac, officer, p)
            self.stdout.write(f"  {state_name}: {'seeded ' + str(seeded) + ' pregnancies' if seeded else 'already seeded'}")

        # Organisation on the Enterprise plan, granted all three states.
        tier = SubscriptionTier.objects.filter(slug="enterprise").first()
        org, _ = Organisation.objects.get_or_create(
            name="National Safe Motherhood Initiative",
            defaults={"org_type": "NGO", "created_by": admin, "tier": tier},
        )
        if tier and org.tier_id != tier.id:
            org.tier = tier
            org.save(update_fields=["tier"])
        for state_name, (state, lga, fac) in facilities.items():
            OrganisationFacilityAccess.objects.get_or_create(
                organisation=org, scope_type=ScopeType.STATE, scope_id=state.id,
                defaults={"access_level": AccessLevel.DE_IDENTIFIED, "granted_by": admin},
            )
        user, created = User.objects.get_or_create(
            email="multi@cureva.care",
            defaults={"name": "Amina (Programme Lead)", "role": Role.ORGANISATION_USER,
                      "organisation": org, "can_manage_org_users": True},
        )
        if created:
            user.set_password("Cureva-test1")
            user.save()

        self.stdout.write(self.style.SUCCESS(
            "\nDemo ready. Login: multi@cureva.care / Cureva-test1 "
            "(National Safe Motherhood Initiative — Enterprise, 3 states)."
        ))

    def _seed_facility(self, fac, officer, p):
        if Woman.objects.filter(facility=fac, name__startswith="Demo ").exists():
            return 0
        intakes = {}

        def row(family):
            ik = intakes.get(family)
            if ik is None:
                ik, _ = Intake.objects.get_or_create(
                    facility=fac, register_family=family, source_hash=f"{fac.id}-{family}-demo",
                    defaults={"submitted_by": officer, "batch_period_from": date(2026, 1, 1), "batch_period_to": date(2026, 12, 31)},
                )
                intakes[family] = ik
            n = SourceRow.objects.filter(intake=ik).count() + 1
            return SourceRow.objects.create(intake=ik, row_number=n, raw_payload={}, normalized={}, status="verified", extraction_confidence={})

        n = p["n"]
        for i in range(n):
            delivered = i < p["births"]
            still = i < p["still"]
            died = i < p["deaths"]
            anc4 = i < p["anc4"]
            screened = i < p["screened"]
            early = i < p["early"]
            high = (not delivered) and (i >= n - p["high"])
            mod = (not delivered) and (not high) and (i >= n - p["high"] - p["mod"])
            pnc = delivered and i < p["pnc"]
            month = (i % 10) + 1

            # Spread age across bands (incl. a few teens and 35+) and parity so
            # the equity breakdowns show real variation, not one "Unknown" group.
            age = [18, 24, 28, 31, 37][i % 5]
            parity = [0, 1, 2, 4, 6][i % 5]
            woman = Woman.objects.create(facility=fac, name=f"Demo W{i + 1}", stable_identifier=f"{fac.id}-{i + 1}", age=age)
            ep = PregnancyEpisode.objects.create(woman=woman, facility=fac, booking_date=date(2026, month, 5), booking_gestational_age_weeks=10 if early else 16)
            for c in range(5 if anc4 else 2):
                data = {"iron_folate_given": "yes", "tetanus_given": "yes", "parity": parity}
                # Most visits record BP + malaria prevention; a minority don't (a real gap).
                if i % 4 != 0:
                    data["blood_pressure"] = "120/80"
                if i % 3 != 0:
                    data["iptp_given"] = "yes"
                if screened:
                    data.update({"hiv_result": "NR", "syphilis_result": "NR", "haemoglobin": "12"})
                if high and c == 0:
                    data["blood_pressure"] = "150/100"
                if mod and c == 0:
                    data["haemoglobin"] = "10"
                ANCContact.objects.create(episode=ep, woman=woman, facility=fac, source_row=row("ANC"), data=data, service_date=date(2026, month, 10 + c))
            if delivered:
                BirthEvent.objects.create(
                    episode=ep, woman=woman, facility=fac, source_row=row("Delivery"), data={},
                    delivery_date=date(2026, month, 20), still_birth=still,
                    maternal_outcome=("died" if died else "alive"), birth_weight_kg=(2.2 if i % 4 == 0 else 3.1),
                    attendant_category=("midwife" if i % 5 != 0 else "traditional birth attendant"),
                )
                if pnc:
                    PNCContact.objects.create(episode=ep, woman=woman, facility=fac, source_row=row("PNC"), data={}, visit_date=date(2026, month, 27))
        return n
