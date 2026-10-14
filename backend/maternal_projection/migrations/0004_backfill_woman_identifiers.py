"""Backfill one card_number identifier per existing woman from her
stable_identifier (IDENTITY_MATCHING_UPDATE.md Section C). Idempotent.

Note: stable_identifier is retained as the woman's primary/canonical card
(denormalised, and the target of the per-facility uniqueness constraint);
woman_identifiers holds the full history that matching reads.
"""
from django.db import migrations


def backfill(apps, schema_editor):
    Woman = apps.get_model("maternal_projection", "Woman")
    WomanIdentifier = apps.get_model("maternal_projection", "WomanIdentifier")
    for woman in Woman.objects.exclude(stable_identifier__isnull=True).exclude(stable_identifier=""):
        exists = WomanIdentifier.objects.filter(
            woman=woman, kind="card_number", value=woman.stable_identifier
        ).exists()
        if not exists:
            WomanIdentifier.objects.create(
                woman=woman, kind="card_number", value=woman.stable_identifier,
                facility_id=woman.facility_id, added_via="backfill",
            )


def unbackfill(apps, schema_editor):
    WomanIdentifier = apps.get_model("maternal_projection", "WomanIdentifier")
    WomanIdentifier.objects.filter(added_via="backfill").delete()


class Migration(migrations.Migration):
    dependencies = [("maternal_projection", "0003_identitycandidate_reason_womanidentifier")]
    operations = [migrations.RunPython(backfill, unbackfill)]
