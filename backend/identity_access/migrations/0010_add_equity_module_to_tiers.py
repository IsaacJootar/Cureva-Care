"""Add the 'equity' module to the seeded Professional & Enterprise tiers
(expansion M6), idempotently (add-only, preserves admin edits).
"""
from django.db import migrations

ADD_TO = {"professional", "enterprise"}
MODULE = "equity"
AFTER = "benchmarking"


def add_module(apps, schema_editor):
    SubscriptionTier = apps.get_model("identity_access", "SubscriptionTier")
    for tier in SubscriptionTier.objects.filter(slug__in=ADD_TO):
        mods = list(tier.modules or [])
        if MODULE not in mods:
            if AFTER in mods:
                mods.insert(mods.index(AFTER) + 1, MODULE)
            else:
                mods.append(MODULE)
            tier.modules = mods
            tier.save(update_fields=["modules"])


def remove_module(apps, schema_editor):
    SubscriptionTier = apps.get_model("identity_access", "SubscriptionTier")
    for tier in SubscriptionTier.objects.filter(slug__in=ADD_TO):
        tier.modules = [m for m in (tier.modules or []) if m != MODULE]
        tier.save(update_fields=["modules"])


class Migration(migrations.Migration):
    dependencies = [("identity_access", "0009_rebalance_default_tiers")]
    operations = [migrations.RunPython(add_module, remove_module)]
