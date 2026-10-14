"""Refresh shared v1 templates to add always_confirm identity flags and the
optional anc_number field (IDENTITY_MATCHING_UPDATE.md Sections A & E).
Pre-launch seed refresh; post-launch changes go through a new version."""
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
    dependencies = [("register_intake", "0004_refresh_default_templates")]
    operations = [migrations.RunPython(refresh, noop)]
