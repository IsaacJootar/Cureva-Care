"""Identity & Access models.

Owns: users, organisations and their facility/region access grants, roles,
the State -> LGA -> Ward -> Facility administrative hierarchy, platform
configuration, per-user notification preferences, auth tokens, and audit
events. See cureva-docs/02-data-model.md and 04-architecture-and-stack.md.
"""
import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


# --- Enumerations ---------------------------------------------------------
class Role(models.TextChoices):
    DATA_OFFICER = "data_officer", "Data officer"
    FACILITY_LEAD = "facility_lead", "Facility lead"
    ORGANISATION_USER = "organisation_user", "Organisation user"
    SYSTEMS_ADMIN = "systems_admin", "Systems admin"


class ThemePreference(models.TextChoices):
    LIGHT = "light", "Light"
    DARK = "dark", "Dark"
    SYSTEM = "system", "System"


class AccessLevel(models.TextChoices):
    """The three access tiers (cureva-docs/07-security-privacy-access.md)."""

    AGGREGATE = "aggregate", "Aggregate"
    DE_IDENTIFIED = "de_identified", "De-identified"
    IDENTIFIABLE = "identifiable", "Identifiable"


class ScopeType(models.TextChoices):
    FACILITY = "facility", "Facility"
    WARD = "ward", "Ward"
    LOCAL_GOVERNMENT = "local_government", "Local Government Area"
    STATE = "state", "State"


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"
    EMAIL_AND_SMS = "email_and_sms", "Email and SMS"
    NONE = "none", "None"


# --- Administrative hierarchy: State -> LGA -> Ward -> Facility -----------
class State(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class LocalGovernment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    state = models.ForeignKey(
        State, on_delete=models.PROTECT, related_name="local_governments"
    )
    name = models.TextField()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["state", "name"], name="uniq_lga_per_state"
            )
        ]

    def __str__(self):
        return self.name


class Ward(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    local_government = models.ForeignKey(
        LocalGovernment, on_delete=models.PROTECT, related_name="wards"
    )
    name = models.TextField()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["local_government", "name"], name="uniq_ward_per_lga"
            )
        ]

    def __str__(self):
        return self.name


class Facility(models.Model):
    """A facility always belongs to a Ward; its LGA and State are derived by
    joining up (never duplicated onto the row). See 02-data-model.md."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ward = models.ForeignKey(
        Ward, on_delete=models.PROTECT, related_name="facilities"
    )
    name = models.TextField()
    facility_type = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "facilities"

    def __str__(self):
        return self.name

    @property
    def local_government(self):
        return self.ward.local_government

    @property
    def state(self):
        return self.ward.local_government.state

    @property
    def region_path(self):
        """Full location, top-down: 'State · LGA · Ward'. The facility itself is
        named separately; this places it in its ward within the hierarchy."""
        lga = self.ward.local_government
        return f"{lga.state.name} · {lga.name} · {self.ward.name}"


# --- Organisations (the view-only SaaS customer layer) --------------------
class Organisation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    org_type = models.TextField(null=True, blank=True)  # free text, not an enum
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organisations_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OrganisationFacilityAccess(models.Model):
    """Which facilities (or whole regions) an organisation can view, and at
    what tier. A region grant auto-expands to every facility under that node,
    present and future (resolved at query time). See 02-data-model.md."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="facility_access"
    )
    scope_type = models.CharField(max_length=32, choices=ScopeType.choices)
    # scope_id references the facility/ward/LGA/state per scope_type. It is a
    # bare UUID (not a hard FK) because the target table varies by scope_type.
    scope_id = models.UUIDField()
    access_level = models.CharField(
        max_length=32,
        choices=AccessLevel.choices,
        default=AccessLevel.AGGREGATE,  # least-identifiable default (07-security)
    )
    granted_by = models.ForeignKey(
        "User",
        on_delete=models.PROTECT,
        related_name="access_grants_made",
    )  # always a Systems admin; never self-service
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-granted_at"]
        indexes = [models.Index(fields=["organisation", "scope_type"])]


# --- User -----------------------------------------------------------------
class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )  # set only for Organisation user
    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="leads",
    )  # set only for Facility lead
    role = models.CharField(max_length=32, choices=Role.choices)
    can_manage_org_users = models.BooleanField(default=False)
    name = models.TextField()
    email = models.EmailField(unique=True)
    phone = models.TextField(null=True, blank=True)
    theme_preference = models.CharField(
        max_length=16, choices=ThemePreference.choices, default=ThemePreference.SYSTEM
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False
    )  # Django-internal only; not a product role
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        ordering = ["name"]
        constraints = [
            # A user never has both organisation and facility set
            # (02-data-model.md).
            models.CheckConstraint(
                name="user_not_both_org_and_facility",
                check=~(
                    models.Q(organisation__isnull=False)
                    & models.Q(facility__isnull=False)
                ),
            ),
        ]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    # Convenience role predicates ----------------------------------------
    @property
    def is_data_officer(self):
        return self.role == Role.DATA_OFFICER

    @property
    def is_facility_lead(self):
        return self.role == Role.FACILITY_LEAD

    @property
    def is_organisation_user(self):
        return self.role == Role.ORGANISATION_USER

    @property
    def is_systems_admin(self):
        return self.role == Role.SYSTEMS_ADMIN


# --- Platform configuration (admin-tunable; NEVER secrets) ----------------
class PlatformSetting(models.Model):
    """Curated key/value store. Only keys the product defines are writable,
    each with a declared type, default, and admin-facing description. Every
    tunable operational value in the build lives here and only here
    (cureva-docs/02-data-model.md, 04-architecture-and-stack.md)."""

    class ValueType(models.TextChoices):
        INTEGER = "integer", "Integer"
        DECIMAL = "decimal", "Decimal"
        BOOLEAN = "boolean", "Boolean"
        STRING = "string", "String"

    key = models.TextField(primary_key=True)
    value = models.JSONField()
    value_type = models.CharField(max_length=16, choices=ValueType.choices)
    description = models.TextField()
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key


class NotificationPreference(models.Model):
    """Per-user, per-notification-type channel preference. A notification job
    never assumes a channel; it resolves this row (02-data-model.md)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    notification_type = models.TextField()
    channel = models.CharField(
        max_length=16,
        choices=NotificationChannel.choices,
        default=NotificationChannel.EMAIL_AND_SMS,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "notification_type"],
                name="uniq_notification_pref_per_user_type",
            )
        ]


# --- Authentication: magic-link tokens ------------------------------------
class MagicLinkToken(models.Model):
    """Single-use, short-lived magic-link token. Only a hash is stored; the
    raw token is emailed once and never persisted (07-security-privacy)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="magic_links"
    )
    token_hash = models.CharField(max_length=128, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_consumable(self):
        from django.utils import timezone

        return self.used_at is None and self.expires_at > timezone.now()


# --- Audit -----------------------------------------------------------------
class AuditEvent(models.Model):
    """Append-only audit trail for logins, access-grant changes, identity
    views/confirmations, exports, corrections, publications, and role changes
    (cureva-docs/07-security-privacy-access.md). metadata NEVER contains PHI."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events"
    )
    event_type = models.CharField(max_length=64)
    subject_type = models.CharField(max_length=64, null=True, blank=True)
    subject_id = models.UUIDField(null=True, blank=True)
    facility = models.ForeignKey(
        Facility, on_delete=models.SET_NULL, null=True, blank=True
    )
    metadata = models.JSONField(default=dict, blank=True)  # non-PHI only
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
        ]
