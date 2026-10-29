"""Rebalance the seeded tiers so each has real value and no tier hides the
mortality outcome (product-owner decision, 2026-10-29).

- Essentials gains Goals & targets + Reporting reliability.
- Professional gains Deaths & stillbirths (surveillance).

Idempotent ADD only — never removes modules, so any admin customisation is kept.
"""
from django.db import migrations

ADDITIONS = {
    "essentials": ["targets", "rdqa"],
    "professional": ["surveillance"],
}


def add_modules(apps, schema_editor):
    SubscriptionTier = apps.get_model("identity_access", "SubscriptionTier")
    for slug, mods_to_add in ADDITIONS.items():
        tier = SubscriptionTier.objects.filter(slug=slug).first()
        if not tier:
            continue
        mods = list(tier.modules or [])
        changed = False
        for m in mods_to_add:
            if m not in mods:
                mods.append(m)
                changed = True
        if changed:
            tier.modules = mods
            tier.save(update_fields=["modules"])


def noop(apps, schema_editor):
    # Reverse is a no-op: we don't strip modules a tier may now rely on.
    pass


class Migration(migrations.Migration):
    dependencies = [("identity_access", "0008_add_targets_module_to_tiers")]
    operations = [migrations.RunPython(add_modules, noop)]
