"""Seed the State -> LGA -> Ward administrative hierarchy.

Reference data, loaded once from a committed fixture
(identity_access/fixtures/nigeria_geo.json) derived from an authentic
public INEC/GRID3 dataset — never invented per facility
(cureva-docs/02-data-model.md, open decision #7 in 08-delivery-plan.md).

Pilot scope: 10 states (incl. FCT/Abuja, Lagos, Kano). Idempotent:
get_or_create throughout, so re-running adds only what's missing and never
duplicates. Rerun after dropping a new fixture in to extend coverage.

    python manage.py seed_geo
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from identity_access.models import LocalGovernment, State, Ward

FIXTURE = Path(__file__).resolve().parent.parent.parent / "fixtures" / "nigeria_geo.json"


class Command(BaseCommand):
    help = "Seed States, LGAs, and Wards from the bundled authentic fixture."

    @transaction.atomic
    def handle(self, *args, **options):
        if not FIXTURE.exists():
            self.stderr.write(self.style.ERROR(f"Fixture not found: {FIXTURE}"))
            return

        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        s_new = l_new = w_new = 0

        for state_row in data:
            state, created = State.objects.get_or_create(name=state_row["state"])
            s_new += int(created)
            for lga_row in state_row["lgas"]:
                lga, created = LocalGovernment.objects.get_or_create(
                    state=state, name=lga_row["name"]
                )
                l_new += int(created)
                existing = set(
                    Ward.objects.filter(local_government=lga).values_list(
                        "name", flat=True
                    )
                )
                to_create = [
                    Ward(local_government=lga, name=w)
                    for w in lga_row["wards"]
                    if w not in existing
                ]
                Ward.objects.bulk_create(to_create)
                w_new += len(to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Geo seed complete. New rows — states: {s_new}, "
                f"LGAs: {l_new}, wards: {w_new}. "
                f"Totals now — states: {State.objects.count()}, "
                f"LGAs: {LocalGovernment.objects.count()}, "
                f"wards: {Ward.objects.count()}."
            )
        )
