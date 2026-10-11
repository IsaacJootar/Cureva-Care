"""Maternal Projection models.

Owns Woman and (from Module 4) PregnancyEpisode, ANCContact, BirthEvent,
PNCContact, Referral — plus identity candidates and the confirmed source-row ->
Woman linkage. Writes these only from verified source rows; never deletes or
rewrites source data (cureva-docs/02, 04).

Module 3 builds Woman, IdentityCandidate, and SourceRowLink (the linkage). The
remaining maternal event tables arrive in Module 4.
"""
import uuid

from django.db import models


class AccessClass(models.TextChoices):
    AGGREGATE = "aggregate", "Aggregate"
    DE_IDENTIFIED = "de_identified", "De-identified"
    IDENTIFIABLE = "identifiable", "Identifiable"


class LinkMethod(models.TextChoices):
    STRICT = "strict", "Strict identifier"
    CANDIDATE_CONFIRMED = "candidate_confirmed", "Human-confirmed candidate"


class CandidateStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    REJECTED = "rejected", "Rejected"


def generate_internal_id():
    return f"W-{uuid.uuid4().hex[:10].upper()}"


class Woman(models.Model):
    """A canonical woman. Created automatically via a stable-identifier match,
    or via a human-confirmed candidate match — never auto-merged on demographic
    similarity alone (cureva-docs/02)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    internal_id = models.CharField(max_length=20, unique=True, default=generate_internal_id)
    facility = models.ForeignKey(
        "identity_access.Facility", on_delete=models.PROTECT, related_name="women"
    )
    stable_identifier = models.CharField(max_length=128, null=True, blank=True)  # card/folder no
    access_class = models.CharField(
        max_length=16, choices=AccessClass.choices, default=AccessClass.IDENTIFIABLE
    )
    # Demographics used for matching (PHI).
    name = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    phone = models.CharField(max_length=32, null=True, blank=True)
    settlement = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # A stable identifier is unique within a facility (the strict path's
            # exact-match key). NULLs are allowed and don't collide.
            models.UniqueConstraint(
                fields=["facility", "stable_identifier"],
                name="uniq_woman_facility_identifier",
                condition=models.Q(stable_identifier__isnull=False),
            )
        ]
        indexes = [models.Index(fields=["facility", "name"])]

    def __str__(self):
        return f"{self.internal_id} ({self.name or 'unnamed'})"


class SourceRowLink(models.Model):
    """The confirmed linkage from a verified source row to a Woman. Only this
    app writes it. A row contributes to per-woman continuity metrics only once
    it has a link (strict or confirmed candidate) — cureva-docs/02."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_row = models.OneToOneField(
        "register_intake.SourceRow", on_delete=models.CASCADE, related_name="woman_link"
    )
    woman = models.ForeignKey(Woman, on_delete=models.PROTECT, related_name="source_links")
    method = models.CharField(max_length=32, choices=LinkMethod.choices)
    linked_at = models.DateTimeField(auto_now_add=True)
    linked_by = models.ForeignKey(
        "identity_access.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )  # null for the automatic strict path


class IdentityCandidate(models.Model):
    """A probabilistic candidate match awaiting human confirmation. Never
    auto-merged: only a human confirmation links it (cureva-docs/02)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_row = models.ForeignKey(
        "register_intake.SourceRow", on_delete=models.CASCADE, related_name="identity_candidates"
    )
    candidate_woman = models.ForeignKey(
        Woman, on_delete=models.CASCADE, related_name="identity_candidates"
    )
    facility = models.ForeignKey(
        "identity_access.Facility", on_delete=models.PROTECT, related_name="identity_candidates"
    )
    confidence = models.DecimalField(max_digits=4, decimal_places=3)  # 0.000–1.000
    matched_fields = models.JSONField(default=dict)  # which fields contributed, and how
    status = models.CharField(
        max_length=16, choices=CandidateStatus.choices, default=CandidateStatus.PENDING
    )
    reviewed_by = models.ForeignKey(
        "identity_access.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-confidence", "-created_at"]
        indexes = [models.Index(fields=["facility", "status"])]
