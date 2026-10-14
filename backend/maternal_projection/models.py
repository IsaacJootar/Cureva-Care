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


class WomanIdentifier(models.Model):
    """Every identifier a woman has ever been recognised by — card numbers (per
    register family), phones, and name spellings. This is how a second
    pregnancy's new card number, or a different register's number, still resolves
    to the same woman (IDENTITY_MATCHING_UPDATE.md Section C). Phones can be
    shared, so they are never unique and never link on their own."""

    class Kind(models.TextChoices):
        CARD_NUMBER = "card_number", "Card number"
        PHONE = "phone", "Phone"
        NAME_VARIANT = "name_variant", "Name variant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    woman = models.ForeignKey(Woman, on_delete=models.CASCADE, related_name="identifiers")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    value = models.TextField()  # stored normalised
    facility = models.ForeignKey("identity_access.Facility", on_delete=models.PROTECT, related_name="woman_identifiers")
    register_family = models.CharField(max_length=16, null=True, blank=True)  # for card numbers
    first_source_row = models.ForeignKey("register_intake.SourceRow", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    last_seen_at = models.DateField(null=True, blank=True)  # service date of the latest row carrying it
    added_via = models.CharField(max_length=24)  # 'strict' | 'confirmed_candidate' | 'backfill'
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["facility", "kind", "value"])]


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
    # Why this went to review instead of auto-linking (IDENTITY_MATCHING_UPDATE
    # Section B): card_match_name_conflict | card_match_name_missing |
    # card_match_stale | probabilistic (no identifier).
    reason = models.CharField(max_length=32, null=True, blank=True)
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


# --- Maternal domain events (Module 4) ------------------------------------
class EpisodeStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DELIVERED = "delivered", "Delivered"
    CLOSED = "closed", "Closed"


class PregnancyEpisode(models.Model):
    """One pregnancy for one woman. A woman may have multiple episodes over
    time — never 1:1 (cureva-docs/02)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    woman = models.ForeignKey(Woman, on_delete=models.CASCADE, related_name="episodes")
    facility = models.ForeignKey("identity_access.Facility", on_delete=models.PROTECT, related_name="episodes")
    episode_number = models.IntegerField(default=1)
    booking_date = models.DateField(null=True, blank=True)
    lmp = models.DateField(null=True, blank=True)
    edd = models.DateField(null=True, blank=True)
    booking_gestational_age_weeks = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=EpisodeStatus.choices, default=EpisodeStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["facility", "status"]), models.Index(fields=["woman", "episode_number"])]


class _MaternalEventBase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episode = models.ForeignKey(PregnancyEpisode, on_delete=models.CASCADE, null=True, blank=True)
    woman = models.ForeignKey(Woman, on_delete=models.CASCADE)
    facility = models.ForeignKey("identity_access.Facility", on_delete=models.PROTECT)
    source_row = models.OneToOneField("register_intake.SourceRow", on_delete=models.CASCADE, related_name="+")
    data = models.JSONField(default=dict)  # full normalized values for this row
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class ANCContact(_MaternalEventBase):
    service_date = models.DateField(null=True, blank=True)
    contact_number = models.IntegerField(null=True, blank=True)
    gestational_age_weeks = models.IntegerField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["facility", "service_date"]), models.Index(fields=["episode"])]


class BirthEvent(_MaternalEventBase):
    delivery_date = models.DateField(null=True, blank=True)
    delivery_place = models.CharField(max_length=32, null=True, blank=True)
    mode_of_delivery = models.CharField(max_length=32, null=True, blank=True)
    attendant_category = models.CharField(max_length=32, null=True, blank=True)
    maternal_outcome = models.CharField(max_length=32, null=True, blank=True)
    baby_outcome = models.CharField(max_length=32, null=True, blank=True)
    still_birth = models.BooleanField(null=True, blank=True)
    birth_weight_kg = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    baby_sex = models.CharField(max_length=8, null=True, blank=True)
    babies = models.JSONField(default=list)  # one entry per baby (multi-baby support)
    referral_status = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["facility", "delivery_date"]), models.Index(fields=["episode"])]


class PNCContact(_MaternalEventBase):
    class Subject(models.TextChoices):
        MOTHER = "mother", "Mother"
        NEWBORN = "newborn", "Newborn"

    visit_date = models.DateField(null=True, blank=True)
    days_postpartum = models.IntegerField(null=True, blank=True)
    subject = models.CharField(max_length=16, choices=Subject.choices, null=True, blank=True)
    feeding_status = models.CharField(max_length=32, null=True, blank=True)
    family_planning = models.CharField(max_length=32, null=True, blank=True)
    visit_outcome = models.CharField(max_length=32, null=True, blank=True)
    referral_status = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["facility", "visit_date"]), models.Index(fields=["episode"])]


class Referral(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed with documented outcome"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episode = models.ForeignKey(PregnancyEpisode, on_delete=models.CASCADE, null=True, blank=True, related_name="referrals")
    woman = models.ForeignKey(Woman, on_delete=models.CASCADE, related_name="referrals")
    facility = models.ForeignKey("identity_access.Facility", on_delete=models.PROTECT, related_name="referrals")
    source_row = models.ForeignKey("register_intake.SourceRow", on_delete=models.CASCADE, related_name="+")
    origin = models.CharField(max_length=16)  # 'Delivery' | 'PNC' | 'ANC'
    reason = models.TextField(null=True, blank=True)
    destination = models.TextField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    outcome = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["facility", "status"])]
