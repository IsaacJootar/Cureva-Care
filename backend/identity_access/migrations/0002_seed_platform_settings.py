"""Seed the platform_settings table with its default rows.

Every tunable value ships with a sensible default at migration time, so the
system is fully operational before an admin ever opens /admin/settings —
"configurable" never means "unset" (cureva-docs/02-data-model.md). Idempotent:
re-running never overwrites an admin's later edit.
"""
from django.db import migrations

# Imported at migration-build time from the authoritative registry so the
# defaults live in exactly one place.
from identity_access.settings_registry import SETTING_DEFINITIONS


def seed_settings(apps, schema_editor):
    PlatformSetting = apps.get_model("identity_access", "PlatformSetting")
    for definition in SETTING_DEFINITIONS:
        PlatformSetting.objects.get_or_create(
            key=definition["key"],
            defaults={
                "value": definition["value"],
                "value_type": definition["value_type"],
                "description": definition["description"],
            },
        )


def unseed_settings(apps, schema_editor):
    PlatformSetting = apps.get_model("identity_access", "PlatformSetting")
    keys = [d["key"] for d in SETTING_DEFINITIONS]
    PlatformSetting.objects.filter(key__in=keys).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("identity_access", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_settings, unseed_settings),
    ]
