"""Operations endpoints — platform settings, notification preferences, and the
rest of user management (cureva-docs/05, Module 6).
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .entitlements import INTEL_MODULES, MODULE_KEYS
from .models import AuditEvent, NotificationPreference, PlatformSetting, Role, SubscriptionTier, User
from .permissions import IsSystemsAdmin
from .serializers import (
    NotificationPreferenceSerializer,
    PlatformSettingSerializer,
    UserSerializer,
)
from .services import SettingValidationError, set_setting


# --- Intelligence tiers / entitlements (Systems admin) --------------------
def _tier_dict(t):
    return {"id": str(t.id), "name": t.name, "slug": t.slug, "modules": t.modules or [], "order": t.order}


class TiersView(APIView):
    """GET /tiers — the module catalogue + every tier's module composition.
    Admin configures which modules each tier includes (nothing hard-coded)."""

    permission_classes = [IsSystemsAdmin]

    def get(self, request):
        return Response({
            "modules": INTEL_MODULES,
            "tiers": [_tier_dict(t) for t in SubscriptionTier.objects.all()],
        })


class TierUpdateView(APIView):
    """PATCH /tiers/{id} — set a tier's modules (and optionally name/order)."""

    permission_classes = [IsSystemsAdmin]

    def patch(self, request, tier_id):
        tier = SubscriptionTier.objects.filter(pk=tier_id).first()
        if tier is None:
            return Response(status=404)
        if "modules" in request.data:
            modules = request.data.get("modules") or []
            if not isinstance(modules, list) or any(m not in MODULE_KEYS for m in modules):
                return Response({"detail": "modules must be a list of valid module keys."}, status=400)
            tier.modules = modules
        if "name" in request.data and str(request.data["name"]).strip():
            tier.name = str(request.data["name"]).strip()
        if "order" in request.data:
            try:
                tier.order = int(request.data["order"])
            except (TypeError, ValueError):
                pass
        tier.save()
        AuditEvent.objects.create(actor=request.user, event_type="tier_updated", subject_type="tier", subject_id=tier.id, metadata={"modules": tier.modules})
        return Response(_tier_dict(tier))


# --- Platform settings (Systems admin) ------------------------------------
class SettingsListView(APIView):
    permission_classes = [IsSystemsAdmin]

    def get(self, request):
        return Response(PlatformSettingSerializer(PlatformSetting.objects.all(), many=True).data)


class SettingUpdateView(APIView):
    permission_classes = [IsSystemsAdmin]

    def patch(self, request, key):
        if not PlatformSetting.objects.filter(pk=key).exists():
            return Response(status=404)
        try:
            row = set_setting(key, request.data.get("value"), updated_by=request.user)
        except SettingValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        AuditEvent.objects.create(
            actor=request.user, event_type="platform_setting_updated",
            subject_type="platform_setting", metadata={"key": key},
        )
        return Response(PlatformSettingSerializer(row).data)


# --- Notification preferences (self-service) -------------------------------
class NotificationPreferencesView(APIView):
    """GET /users/{id}/notification-preferences — a user's own channel prefs."""

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if str(request.user.id) != str(user_id):
            return Response(status=403)
        prefs = NotificationPreference.objects.filter(user=request.user)
        return Response(NotificationPreferenceSerializer(prefs, many=True).data)


class NotificationPreferenceUpdateView(APIView):
    """PATCH /users/{id}/notification-preferences/{type} — self-service channel."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id, notification_type):
        if str(request.user.id) != str(user_id):
            return Response(status=403)
        channel = request.data.get("channel")
        valid = {"email", "sms", "email_and_sms", "none"}
        if channel not in valid:
            return Response({"detail": f"channel must be one of {sorted(valid)}."}, status=400)
        pref, _ = NotificationPreference.objects.get_or_create(
            user=request.user, notification_type=notification_type
        )
        pref.channel = channel
        pref.save(update_fields=["channel", "updated_at"])
        return Response(NotificationPreferenceSerializer(pref).data)


# --- User management (Systems admin) ---------------------------------------
class UserEditView(APIView):
    """PATCH /users/{id} — admin edits name or role (not self-service)."""

    permission_classes = [IsSystemsAdmin]

    def patch(self, request, user_id):
        user = User.objects.filter(pk=user_id).first()
        if user is None:
            return Response(status=404)
        if "name" in request.data:
            user.name = request.data["name"]
        if "role" in request.data:
            new_role = request.data["role"]
            if new_role not in Role.values:
                return Response({"detail": "Invalid role."}, status=400)
            user.role = new_role
        user.save(update_fields=["name", "role"])
        AuditEvent.objects.create(
            actor=request.user, event_type="user_edited",
            subject_type="user", subject_id=user.id, metadata={"role": user.role},
        )
        return Response(UserSerializer(user).data)


class UserDeactivateView(APIView):
    permission_classes = [IsSystemsAdmin]

    def post(self, request, user_id):
        user = User.objects.filter(pk=user_id).first()
        if user is None:
            return Response(status=404)
        user.is_active = False
        user.save(update_fields=["is_active"])
        AuditEvent.objects.create(actor=request.user, event_type="user_deactivated", subject_type="user", subject_id=user.id)
        return Response({"status": "deactivated"})


class UserReactivateView(APIView):
    permission_classes = [IsSystemsAdmin]

    def post(self, request, user_id):
        user = User.objects.filter(pk=user_id).first()
        if user is None:
            return Response(status=404)
        user.is_active = True
        user.save(update_fields=["is_active"])
        AuditEvent.objects.create(actor=request.user, event_type="user_reactivated", subject_type="user", subject_id=user.id)
        return Response({"status": "reactivated"})


class UserSetPasswordView(APIView):
    """POST /users/{id}/set-password — admin sets/resets a user's password.
    If no password is supplied, a readable one is generated and returned once."""

    permission_classes = [IsSystemsAdmin]

    def post(self, request, user_id):
        import secrets

        user = User.objects.filter(pk=user_id).first()
        if user is None:
            return Response(status=404)
        password = request.data.get("password") or None
        generated = None
        if not password:
            generated = f"Cureva-{secrets.token_urlsafe(6)}"
            password = generated
        elif len(password) < 8:
            return Response({"detail": "Password must be at least 8 characters."}, status=400)
        user.set_password(password)
        user.save(update_fields=["password"])
        AuditEvent.objects.create(actor=request.user, event_type="user_password_reset", subject_type="user", subject_id=user.id)
        return Response({"status": "password_set", "initial_password": generated})


class UserFacilityView(APIView):
    """PATCH /users/{id}/facility — admin assigns a Facility lead's facility."""

    permission_classes = [IsSystemsAdmin]

    def patch(self, request, user_id):
        user = User.objects.filter(pk=user_id, role=Role.FACILITY_LEAD).first()
        if user is None:
            return Response({"detail": "No such Facility lead."}, status=404)
        from .models import Facility

        facility_id = request.data.get("facility")
        if not Facility.objects.filter(pk=facility_id).exists():
            return Response({"detail": "Unknown facility."}, status=400)
        user.facility_id = facility_id
        user.save(update_fields=["facility"])
        return Response(UserSerializer(user).data)


class OrgUserDeleteView(APIView):
    """DELETE /organisations/{id}/users/{userId} — the single write an
    Organisation user can make: deactivate a colleague in their OWN
    organisation (soft delete), gated on can_manage_org_users. Rejected for any
    other combination (cureva-docs/05 "Notes for implementation")."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, user_id):
        actor = request.user
        allowed = (
            actor.role == Role.SYSTEMS_ADMIN
            or (actor.role == Role.ORGANISATION_USER and actor.can_manage_org_users and str(actor.organisation_id) == str(pk))
        )
        if not allowed:
            return Response(status=403)
        target = User.objects.filter(pk=user_id, organisation_id=pk, role=Role.ORGANISATION_USER).first()
        if target is None:
            return Response(status=404)
        target.is_active = False
        target.save(update_fields=["is_active"])
        AuditEvent.objects.create(
            actor=actor, event_type="organisation_user_deactivated",
            subject_type="user", subject_id=target.id, metadata={"organisation_id": str(pk)},
        )
        return Response(status=204)
