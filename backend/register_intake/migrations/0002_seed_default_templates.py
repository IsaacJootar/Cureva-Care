"""Seed the shared/default ANC, Delivery, and PNC templates (v1).

These shared defaults (facility IS NULL) are what every facility resolves to
unless it has its own override — so intake works out of the box. Idempotent.
"""
from datetime import date

from django.db import migrations

from register_intake.default_templates import DEFAULT_TEMPLATES


def seed_templates(apps, schema_editor):
    Template = apps.get_model("register_intake", "Template")
    for schema in DEFAULT_TEMPLATES:
        Template.objects.get_or_create(
            register_family=schema["register_family"],
            facility=None,
            version=schema["version"],
            defaults={
                "effective_date": date.fromisoformat(schema["effective_date"]),
                "is_active": True,
                "schema": schema,
            },
        )


def unseed_templates(apps, schema_editor):
    Template = apps.get_model("register_intake", "Template")
    Template.objects.filter(facility=None, version=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("register_intake", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
