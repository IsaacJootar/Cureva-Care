"""Register Intake models.

Owns files, templates, template flags, batches (intakes), source rows, review,
and publication. Nothing outside this app ever writes a source row
(cureva-docs/03-templates-and-intake.md, 04-architecture-and-stack.md).
"""
import uuid

from django.db import models


class RegisterFamily(models.TextChoices):
    ANC = "ANC", "Antenatal (ANC)"
    DELIVERY = "Delivery", "Delivery"
    PNC = "PNC", "Postnatal (PNC)"


class IntakeStatus(models.TextChoices):
    AWAITING_CONFIRMATION = "awaiting_confirmation", "Awaiting confirmation"
    PUBLISHED = "published", "Published"
    REJECTED = "rejected", "Rejected"
    EXTRACTION_FAILED = "extraction_failed", "Extraction failed"


class SourceRowStatus(models.TextChoices):
    AWAITING_CONFIRMATION = "awaiting_confirmation", "Awaiting confirmation"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"


class RegisterMismatchStatus(models.TextChoices):
    NOT_APPLICABLE = "not_applicable", "Not applicable"
    FLAGGED = "flagged", "Flagged"
    CONFIRMED_AS_DECLARED = "confirmed_as_declared", "Confirmed as declared"
    SWITCHED = "switched", "Switched"


class Template(models.Model):
    """A versioned definition of what one register page should contain. Field
    definitions live in `schema` (JSONB). Per-facility by design, falling back
    to a shared default (facility_id IS NULL) per register family. New changes
    always write a NEW version — never edit a version in place (rule #2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    register_family = models.CharField(max_length=16, choices=RegisterFamily.choices)
    # NULL = shared/default national template; set = facility-specific override.
    facility = models.ForeignKey(
        "identity_access.Facility",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="templates",
    )
    version = models.IntegerField()
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)
    schema = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["register_family", "facility", "version"],
                name="uniq_template_family_facility_version",
            )
        ]
        indexes = [models.Index(fields=["register_family", "facility", "is_active"])]

    def __str__(self):
        scope = "shared" if self.facility_id is None else f"facility {self.facility_id}"
        return f"{self.register_family} v{self.version} ({scope})"


class Intake(models.Model):
    """One facility register batch. Immutable and unique by (facility,
    register_family, source_hash) — a duplicate checksum is a no-op (rule #2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    facility = models.ForeignKey(
        "identity_access.Facility", on_delete=models.PROTECT, related_name="intakes"
    )  # chosen by the data officer at the start of this intake
    submitted_by = models.ForeignKey(
        "identity_access.User", on_delete=models.PROTECT, related_name="intakes_submitted"
    )
    register_family = models.CharField(max_length=16, choices=RegisterFamily.choices)
    template = models.ForeignKey(
        Template, on_delete=models.PROTECT, related_name="intakes", null=True, blank=True
    )  # resolved at validation time; recorded permanently
    extraction_engine = models.CharField(max_length=64, default="")
    source_hash = models.CharField(max_length=128)
    file_path = models.TextField(default="")  # object-storage path/prefix for this batch
    batch_period_from = models.DateField()
    batch_period_to = models.DateField()
    status = models.CharField(
        max_length=32,
        choices=IntakeStatus.choices,
        default=IntakeStatus.AWAITING_CONFIRMATION,
    )
    suspected_register_family = models.CharField(
        max_length=16, choices=RegisterFamily.choices, null=True, blank=True
    )
    register_mismatch_status = models.CharField(
        max_length=32,
        choices=RegisterMismatchStatus.choices,
        default=RegisterMismatchStatus.NOT_APPLICABLE,
    )
    register_mismatch_resolved_by = models.ForeignKey(
        "identity_access.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    register_mismatch_resolved_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "register_family", "source_hash"],
                name="uniq_intake_facility_family_hash",
            )
        ]
        indexes = [
            models.Index(fields=["facility", "status"]),
            models.Index(fields=["submitted_by", "received_at"]),
        ]

    def __str__(self):
        return f"Intake {self.id} ({self.register_family} @ {self.facility_id})"


class IntakeImage(models.Model):
    """One page of a (possibly multi-page) register batch. The intake's
    source_hash is the combined fingerprint over all its pages; each page also
    keeps its own hash for traceability (cureva-docs/03: multi-page batches are
    multiple images against one intake)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intake = models.ForeignKey(Intake, on_delete=models.CASCADE, related_name="images")
    page_number = models.IntegerField()
    object_key = models.TextField()  # private object-storage key for this page
    image_hash = models.CharField(max_length=128)
    source_label = models.CharField(max_length=64, default="")  # "camera" | "upload"
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["page_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["intake", "page_number"], name="uniq_image_page_per_intake"
            )
        ]


class SourceRow(models.Model):
    """One extracted register line. raw_payload is kept untouched forever;
    normalized values live alongside, never in place (rule #1). Every row lands
    as awaiting_confirmation and only publishes after its low-confidence fields
    are human-confirmed (rule #3)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intake = models.ForeignKey(Intake, on_delete=models.CASCADE, related_name="rows")
    row_number = models.IntegerField()
    raw_payload = models.JSONField()  # exactly as extracted from the image
    normalized = models.JSONField(null=True, blank=True)
    service_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=SourceRowStatus.choices,
        default=SourceRowStatus.AWAITING_CONFIRMATION,
    )
    flags = models.JSONField(null=True, blank=True)  # plausibility warnings
    extraction_confidence = models.JSONField(default=dict)  # {"field": 0.0-1.0}
    field_image_regions = models.JSONField(null=True, blank=True)  # {"field": crop}
    confirmed_by = models.ForeignKey(
        "identity_access.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["intake", "row_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["intake", "row_number"], name="uniq_row_per_intake"
            )
        ]
        indexes = [models.Index(fields=["intake", "status"])]


class FieldCorrection(models.Model):
    """Append-only correction history. The AI's (or an earlier) value is never
    silently lost — it's kept alongside the human's corrected value (rule #1,
    cureva-docs/02 "correction history")."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_row = models.ForeignKey(
        SourceRow, on_delete=models.CASCADE, related_name="corrections"
    )
    field = models.CharField(max_length=128)
    previous_value = models.JSONField(null=True, blank=True)
    corrected_value = models.JSONField(null=True, blank=True)
    corrected_by = models.ForeignKey(
        "identity_access.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    corrected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["corrected_at"]


class TemplateFlag(models.Model):
    """A data officer's lightweight 'this doesn't look right' report. Flagging
    never creates/changes a template — only a Systems admin can turn a flag
    into an official template (cureva-docs/03 governance boundary)."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intake = models.ForeignKey(Intake, on_delete=models.CASCADE, related_name="flags")
    flagged_by = models.ForeignKey(
        "identity_access.User", on_delete=models.PROTECT, related_name="template_flags"
    )
    note = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    resolved_by = models.ForeignKey(
        "identity_access.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    resolved_template = models.ForeignKey(
        Template, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_flags"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
