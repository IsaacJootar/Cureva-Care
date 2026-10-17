"""Seed the intelligence early-warning platform settings (idempotent).

Adds coverage_alert_floor, referral_backlog_days, severe_cluster_rate, and
high_risk_contact_gap_days (11-intelligence-module.md WS5). get_or_create skips
any already present.
"""
from django.db import migrations

from identity_access.settings_registry import SETTING_DEFINITIONS

_NEW_KEYS = ["coverage_alert_floor", "referral_backlog_days", "severe_cluster_rate", "high_risk_contact_gap_days"]


def seed(apps, schema_editor):
    PlatformSetting = apps.get_model("identity_access", "PlatformSetting")
    by_key = {d["key"]: d for d in SETTING_DEFINITIONS}
    for key in _NEW_KEYS:
        d = by_key[key]
        PlatformSetting.objects.get_or_create(
            key=d["key"],
            defaults={"value": d["value"], "value_type": d["value_type"], "description": d["description"]},
        )


def unseed(apps, schema_editor):
    PlatformSetting = apps.get_model("identity_access", "PlatformSetting")
    PlatformSetting.objects.filter(key__in=_NEW_KEYS).delete()


class Migration(migrations.Migration):
    dependencies = [("identity_access", "0003_seed_identity_settings")]
    operations = [migrations.RunPython(seed, unseed)]
