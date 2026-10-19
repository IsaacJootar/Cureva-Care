"""Seed the default subscription tiers (idempotent).

Essentials / Professional / Enterprise with a sensible default module
composition (admin-editable afterwards). See identity_access.entitlements.
"""
from django.db import migrations

from identity_access.entitlements import DEFAULT_TIERS


def seed(apps, schema_editor):
    SubscriptionTier = apps.get_model("identity_access", "SubscriptionTier")
    for t in DEFAULT_TIERS:
        SubscriptionTier.objects.get_or_create(
            slug=t["slug"],
            defaults={"name": t["name"], "modules": t["modules"], "order": t["order"]},
        )


def unseed(apps, schema_editor):
    SubscriptionTier = apps.get_model("identity_access", "SubscriptionTier")
    SubscriptionTier.objects.filter(slug__in=[t["slug"] for t in DEFAULT_TIERS]).delete()


class Migration(migrations.Migration):
    dependencies = [("identity_access", "0005_subscriptiontier_organisation_extra_modules_and_more")]
    operations = [migrations.RunPython(seed, unseed)]
