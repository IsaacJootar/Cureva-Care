"""Add the new 'coverage' module to the seeded Professional & Enterprise tiers
(expansion M1), idempotently. Admins can still re-tick afterwards.
"""
from django.db import migrations

ADD_TO = {"professional", "enterprise"}
MODULE = "coverage"


def add_coverage(apps, schema_editor):
    SubscriptionTier = apps.get_model("identity_access", "SubscriptionTier")
    for tier in SubscriptionTier.objects.filter(slug__in=ADD_TO):
        mods = list(tier.modules or [])
        if MODULE not in mods:
            # keep it next to care_journey if present, else append
            if "care_journey" in mods:
                mods.insert(mods.index("care_journey") + 1, MODULE)
            else:
                mods.append(MODULE)
            tier.modules = mods
            tier.save(update_fields=["modules"])


def remove_coverage(apps, schema_editor):
    SubscriptionTier = apps.get_model("identity_access", "SubscriptionTier")
    for tier in SubscriptionTier.objects.filter(slug__in=ADD_TO):
        mods = [m for m in (tier.modules or []) if m != MODULE]
        tier.modules = mods
        tier.save(update_fields=["modules"])


class Migration(migrations.Migration):
    dependencies = [("identity_access", "0006_seed_subscription_tiers")]
    operations = [migrations.RunPython(add_coverage, remove_coverage)]
