"""Reporting models — saved analytical briefs and export audit.

Bounded, access-level-filtered access to source rows only (cureva-docs/04).
"""
import uuid

from django.db import models


class SavedReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.TextField()
    facility_ids = models.JSONField(default=list)  # the scope this brief was generated for
    period_from = models.DateField(null=True, blank=True)
    period_to = models.DateField(null=True, blank=True)
    sections = models.JSONField(default=dict)  # deterministic metrics/charts data
    narrative = models.TextField(null=True, blank=True)  # optional aggregate-only LLM prose
    generated_by = models.ForeignKey("identity_access.User", on_delete=models.SET_NULL, null=True, related_name="reports")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ExportAudit(models.Model):
    """Every data export is an auditable event (cureva-docs/07)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exported_by = models.ForeignKey("identity_access.User", on_delete=models.SET_NULL, null=True, related_name="exports")
    export_type = models.CharField(max_length=32)  # 'records_csv' | 'report'
    access_level = models.CharField(max_length=16)
    facility_ids = models.JSONField(default=list)
    row_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
