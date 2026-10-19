"""Serializers for Identity & Access resources."""
import secrets

from rest_framework import serializers

from .models import (
    AccessLevel,
    Facility,
    LocalGovernment,
    NotificationPreference,
    Organisation,
    OrganisationFacilityAccess,
    PlatformSetting,
    Role,
    ScopeType,
    State,
    User,
    Ward,
)


# --- Geo hierarchy --------------------------------------------------------
class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name"]


class LocalGovernmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalGovernment
        fields = ["id", "name", "state"]


class WardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = ["id", "name", "local_government"]


class FacilitySerializer(serializers.ModelSerializer):
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    local_government_name = serializers.CharField(
        source="ward.local_government.name", read_only=True
    )
    state_name = serializers.CharField(
        source="ward.local_government.state.name", read_only=True
    )

    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "facility_type",
            "is_active",
            "ward",
            "ward_name",
            "local_government_name",
            "state_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class FacilityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ["id", "name", "facility_type", "ward", "is_active"]
        read_only_fields = ["id"]

    def validate_ward(self, value):
        # A facility cannot be created without a ward (and therefore an LGA and
        # State) — there is no "unassigned" facility (02-data-model.md).
        if value is None:
            raise serializers.ValidationError("A ward is required.")
        return value


# --- Organisations --------------------------------------------------------
class OrganisationFacilityAccessSerializer(serializers.ModelSerializer):
    scope_label = serializers.SerializerMethodField()

    class Meta:
        model = OrganisationFacilityAccess
        fields = [
            "id",
            "organisation",
            "scope_type",
            "scope_id",
            "access_level",
            "scope_label",
            "granted_at",
        ]
        read_only_fields = ["id", "organisation", "granted_at"]

    def get_scope_label(self, obj):
        model_by_scope = {
            ScopeType.FACILITY: Facility,
            ScopeType.WARD: Ward,
            ScopeType.LOCAL_GOVERNMENT: LocalGovernment,
            ScopeType.STATE: State,
        }
        model = model_by_scope.get(obj.scope_type)
        if not model:
            return None
        row = model.objects.filter(pk=obj.scope_id).first()
        return row.name if row else None


class OrganisationFacilityAccessCreateSerializer(serializers.Serializer):
    scope_type = serializers.ChoiceField(choices=ScopeType.choices)
    scope_id = serializers.UUIDField()
    access_level = serializers.ChoiceField(
        choices=AccessLevel.choices, default=AccessLevel.AGGREGATE
    )

    def validate(self, attrs):
        model_by_scope = {
            ScopeType.FACILITY: Facility,
            ScopeType.WARD: Ward,
            ScopeType.LOCAL_GOVERNMENT: LocalGovernment,
            ScopeType.STATE: State,
        }
        model = model_by_scope[attrs["scope_type"]]
        if not model.objects.filter(pk=attrs["scope_id"]).exists():
            raise serializers.ValidationError(
                {"scope_id": f"No {attrs['scope_type']} with that id exists."}
            )
        return attrs


class OrganisationSerializer(serializers.ModelSerializer):
    facility_access = OrganisationFacilityAccessSerializer(many=True, read_only=True)
    active_user_count = serializers.SerializerMethodField()
    access_summary = serializers.SerializerMethodField()
    tier_name = serializers.CharField(source="tier.name", read_only=True)
    entitled_modules = serializers.SerializerMethodField()

    def get_entitled_modules(self, obj):
        mods = set(obj.tier.modules or []) if obj.tier_id else set()
        mods |= set(obj.extra_modules or [])
        return sorted(mods)

    def validate_extra_modules(self, value):
        from .entitlements import MODULE_KEYS

        if not isinstance(value, list) or any(m not in MODULE_KEYS for m in value):
            raise serializers.ValidationError("Must be a list of valid module keys.")
        return value

    class Meta:
        model = Organisation
        fields = [
            "id",
            "name",
            "org_type",
            "is_active",
            "tier",
            "tier_name",
            "extra_modules",
            "entitled_modules",
            "facility_access",
            "active_user_count",
            "access_summary",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_active_user_count(self, obj):
        return obj.users.filter(is_active=True).count()

    def get_access_summary(self, obj):
        grants = list(obj.facility_access.all())
        if not grants:
            return "No access granted"
        facilities = sum(1 for g in grants if g.scope_type == ScopeType.FACILITY)
        regions = len(grants) - facilities
        parts = []
        if facilities:
            parts.append(f"{facilities} facilit{'y' if facilities == 1 else 'ies'}")
        if regions:
            parts.append(f"{regions} region{'' if regions == 1 else 's'}")
        return " · ".join(parts)


# --- Users ----------------------------------------------------------------
class UserSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source="facility.name", read_only=True)
    organisation_name = serializers.CharField(
        source="organisation.name", read_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "role",
            "phone",
            "facility",
            "facility_name",
            "organisation",
            "organisation_name",
            "can_manage_org_users",
            "theme_preference",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    # Admin may set an initial password; if omitted, one is generated and
    # returned ONCE (in initial_password) for the admin to share with the user.
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=8)
    initial_password = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "role",
            "phone",
            "facility",
            "organisation",
            "can_manage_org_users",
            "password",
            "initial_password",
        ]
        read_only_fields = ["id"]

    def get_initial_password(self, obj):
        return getattr(obj, "_initial_password", None)

    def validate(self, attrs):
        role = attrs.get("role")
        facility = attrs.get("facility")
        organisation = attrs.get("organisation")

        # A Systems admin never creates an Organisation user through the
        # generic /users endpoint except as an organisation's first user; that
        # path is handled explicitly elsewhere. Guard the invariants here.
        if role == Role.FACILITY_LEAD and facility is None:
            raise serializers.ValidationError(
                {"facility": "A Facility lead must be assigned a facility."}
            )
        if role != Role.FACILITY_LEAD and facility is not None:
            raise serializers.ValidationError(
                {"facility": "Only a Facility lead has a facility assignment."}
            )
        if role == Role.ORGANISATION_USER and organisation is None:
            raise serializers.ValidationError(
                {"organisation": "An Organisation user must belong to an organisation."}
            )
        if role != Role.ORGANISATION_USER and organisation is not None:
            raise serializers.ValidationError(
                {"organisation": "Only an Organisation user belongs to an organisation."}
            )
        if role != Role.ORGANISATION_USER and attrs.get("can_manage_org_users"):
            raise serializers.ValidationError(
                {"can_manage_org_users": "Only meaningful for an Organisation user."}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None) or None
        generated = None
        if not password:
            generated = f"Cureva-{secrets.token_urlsafe(6)}"  # readable, shareable
            password = generated
        user = User.objects.create_user(password=password, **validated_data)
        user._initial_password = generated  # only surfaced when auto-generated
        return user


class SelfUserSerializer(serializers.ModelSerializer):
    """What a signed-in user sees/edits about themselves. Name is editable;
    email and role are never self-service (05-api-routes.md)."""

    facility_name = serializers.CharField(source="facility.name", read_only=True)
    organisation_name = serializers.CharField(
        source="organisation.name", read_only=True
    )
    entitled_modules = serializers.SerializerMethodField()

    def get_entitled_modules(self, obj):
        from .entitlements import entitled_modules
        return sorted(entitled_modules(obj))

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "role",
            "facility",
            "facility_name",
            "organisation",
            "organisation_name",
            "can_manage_org_users",
            "theme_preference",
            "entitled_modules",
        ]
        read_only_fields = [
            "id",
            "email",
            "role",
            "facility",
            "organisation",
            "can_manage_org_users",
        ]


# --- Platform settings & notification preferences -------------------------
class PlatformSettingSerializer(serializers.ModelSerializer):
    default = serializers.SerializerMethodField()

    class Meta:
        model = PlatformSetting
        fields = ["key", "value", "value_type", "description", "default", "updated_at"]
        read_only_fields = ["key", "value_type", "description", "updated_at"]

    def get_default(self, obj):
        from .settings_registry import DEFAULTS_BY_KEY

        definition = DEFAULTS_BY_KEY.get(obj.key)
        return definition["value"] if definition else None


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["id", "notification_type", "channel", "updated_at"]
        read_only_fields = ["id", "notification_type", "updated_at"]
