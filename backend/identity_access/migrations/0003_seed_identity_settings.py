"""Seed the new identity-matching platform settings (idempotent).

Adds identity_strict_name_floor, identity_card_reuse_window_days, and
new_episode_gap_days (IDENTITY_MATCHING_UPDATE.md). get_or_create skips any
already present, so this only adds the new keys.
"""
from django.db import migrations

from identity_access.settings_registry import SETTING_DEFINITIONS


def seed(apps, schema_editor):
    PlatformSetting = apps.get_model("identity_access", "PlatformSetting")
    for d in SETTING_DEFINITIONS:
        PlatformSetting.objects.get_or_create(
            key=d["key"],
            defaults={"value": d["value"], "value_type": d["value_type"], "description": d["description"]},
        )


def unseed(apps, schema_editor):
    PlatformSetting = apps.get_model("identity_access", "PlatformSetting")
    PlatformSetting.objects.filter(
        key__in=["identity_strict_name_floor", "identity_card_reuse_window_days", "new_episode_gap_days"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("identity_access", "0002_seed_platform_settings")]
    operations = [migrations.RunPython(seed, unseed)]
