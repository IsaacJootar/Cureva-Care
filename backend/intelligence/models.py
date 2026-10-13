"""Intelligence models — metric aggregates, worklist actions, exports.

Owns metric definitions and aggregates; never makes clinical treatment
decisions (cureva-docs/04). DailyFacilityMetric is the precomputed per-facility,
per-service-day aggregate refreshed idempotently after each publish.
"""
import uuid

from django.db import models


class DailyFacilityMetric(models.Model):
    """Per facility, per service date (rule #4: service_date, never upload
    date). Rebuilt idempotently from the projected maternal events."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    facility = models.ForeignKey("identity_access.Facility", on_delete=models.CASCADE, related_name="daily_metrics")
    day = models.DateField()
    anc_contacts = models.IntegerField(default=0)
    deliveries = models.IntegerField(default=0)
    pnc_contacts = models.IntegerField(default=0)
    open_referrals = models.IntegerField(default=0)
    closed_referrals = models.IntegerField(default=0)
    live_births = models.IntegerField(default=0)
    still_births = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["facility", "day"], name="uniq_daily_metric_facility_day")
        ]
        indexes = [models.Index(fields=["facility", "day"])]


class WorklistAction(models.Model):
    """Audit overlay recording that a Facility lead followed up on a worklist
    item — never a mutation of register data or referral_status (cureva-docs/02).
    Built in Module 5; defined here as it belongs to Intelligence."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule_key = models.CharField(max_length=64)
    subject_type = models.CharField(max_length=32)
    subject_id = models.UUIDField()
    facility = models.ForeignKey("identity_access.Facility", on_delete=models.CASCADE, related_name="worklist_actions")
    note = models.TextField(null=True, blank=True)
    actioned_by = models.ForeignKey("identity_access.User", on_delete=models.PROTECT, related_name="worklist_actions")
    actioned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-actioned_at"]
        indexes = [models.Index(fields=["rule_key", "subject_id"])]
