"""Refresh the shared v1 template schemas after reconciling Delivery/PNC
against the real NHMIS registers (open decision #1). Pre-launch seed
correction — no real intakes have used these yet; post-launch changes go
through a new version, never in-place (rule #2)."""
from django.db import migrations

from register_intake.default_templates import DEFAULT_TEMPLATES


def refresh(apps, schema_editor):
    Template = apps.get_model("register_intake", "Template")
    for schema in DEFAULT_TEMPLATES:
        Template.objects.filter(
            register_family=schema["register_family"], facility__isnull=True, version=1
        ).update(schema=schema)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("register_intake", "0003_sourcerow_confirmed_fields_and_more"),
    ]

    operations = [migrations.RunPython(refresh, noop)]
