"""Serializers for the Register Intake API."""
from rest_framework import serializers

from identity_access.services import get_setting
from identity_access.settings_registry import AI_EXTRACTION_CONFIDENCE_THRESHOLD

from .models import Intake, SourceRow, Template, TemplateFlag
from .pipeline import row_needs_confirmation


class SourceRowSerializer(serializers.ModelSerializer):
    needs_confirmation = serializers.SerializerMethodField()

    class Meta:
        model = SourceRow
        fields = [
            "id",
            "row_number",
            "raw_payload",
            "normalized",
            "service_date",
            "status",
            "flags",
            "extraction_confidence",
            "confirmed_fields",
            "unmatched_labels",
            "needs_confirmation",
        ]

    def get_needs_confirmation(self, obj):
        threshold = float(get_setting(AI_EXTRACTION_CONFIDENCE_THRESHOLD))
        return row_needs_confirmation(obj, threshold)


class IntakeSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source="facility.name", read_only=True)
    row_count = serializers.SerializerMethodField()
    page_count = serializers.SerializerMethodField()

    class Meta:
        model = Intake
        fields = [
            "id",
            "facility",
            "facility_name",
            "register_family",
            "template",
            "extraction_engine",
            "status",
            "suspected_register_family",
            "register_mismatch_status",
            "batch_period_from",
            "batch_period_to",
            "source_hash",
            "received_at",
            "published_at",
            "row_count",
            "page_count",
        ]
        read_only_fields = fields

    def get_row_count(self, obj):
        return obj.rows.count()

    def get_page_count(self, obj):
        return obj.images.count()


class TemplateSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source="facility.name", read_only=True, default=None)
    column_count = serializers.SerializerMethodField()

    class Meta:
        model = Template
        fields = [
            "id",
            "register_family",
            "facility",
            "facility_name",
            "version",
            "effective_date",
            "is_active",
            "schema",
            "column_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "column_count"]

    def get_column_count(self, obj):
        return len(obj.schema.get("columns", []))


class TemplateFlagSerializer(serializers.ModelSerializer):
    flagged_by_name = serializers.CharField(source="flagged_by.name", read_only=True)

    class Meta:
        model = TemplateFlag
        fields = ["id", "intake", "flagged_by", "flagged_by_name", "note", "status", "created_at"]
        read_only_fields = ["id", "flagged_by", "flagged_by_name", "status", "created_at"]
