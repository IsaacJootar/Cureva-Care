"""Seed the default program targets (expansion M7), idempotently.
WHO/SDG-aligned starting percentages; admin-editable afterwards.
"""
from django.db import migrations

from intelligence.targets import DEFAULT_TARGETS


def seed(apps, schema_editor):
    ProgramTarget = apps.get_model("intelligence", "ProgramTarget")
    for t in DEFAULT_TARGETS:
        ProgramTarget.objects.get_or_create(
            key=t["key"],
            defaults={"target_pct": t["target_pct"], "order": t["order"], "is_active": True},
        )


def unseed(apps, schema_editor):
    ProgramTarget = apps.get_model("intelligence", "ProgramTarget")
    ProgramTarget.objects.filter(key__in=[t["key"] for t in DEFAULT_TARGETS]).delete()


class Migration(migrations.Migration):
    dependencies = [("intelligence", "0003_programtarget")]
    operations = [migrations.RunPython(seed, unseed)]
