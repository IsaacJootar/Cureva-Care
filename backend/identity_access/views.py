"""Identity & Access resource endpoints.

Facility creation, organisation management + access grants, user creation, the
geo pickers, and the self-service "me" endpoint. Role checks are server-side
(cureva-docs/05-api-routes.md).
"""
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AuditEvent,
    Facility,
    LocalGovernment,
    Organisation,
    OrganisationFacilityAccess,
    Role,
    State,
    User,
    Ward,
)
from .permissions import IsSystemsAdmin
from .serializers import (
    FacilityCreateSerializer,
    FacilitySerializer,
    LocalGovernmentSerializer,
    OrganisationFacilityAccessCreateSerializer,
    OrganisationFacilityAccessSerializer,
    OrganisationSerializer,
    SelfUserSerializer,
    StateSerializer,
    UserCreateSerializer,
    UserSerializer,
    WardSerializer,
)


# --- Me --------------------------------------------------------------------
class MeView(APIView):
    """GET/PATCH /users/me — the signed-in user's own record.

    PATCH only ever changes the caller's own name and theme preference; email
    and role are never self-service and are rejected here (05-api-routes.md).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(SelfUserSerializer(request.user).data)

    def patch(self, request):
        for forbidden in ("role", "email", "facility", "organisation"):
            if forbidden in request.data:
                return Response(
                    {forbidden: "This field is not self-service."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        allowed = {}
        if "name" in request.data:
            allowed["name"] = request.data["name"]
        if "theme_preference" in request.data:
            allowed["theme_preference"] = request.data["theme_preference"]
        serializer = SelfUserSerializer(
            request.user, data=allowed, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# --- Geo pickers -----------------------------------------------------------
class StateListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StateSerializer
    pagination_class = None
    queryset = State.objects.all()


class LocalGovernmentListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LocalGovernmentSerializer
    pagination_class = None

    def get_queryset(self):
        return LocalGovernment.objects.filter(state_id=self.kwargs["state_id"])


class WardListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WardSerializer
    pagination_class = None

    def get_queryset(self):
        return Ward.objects.filter(local_government_id=self.kwargs["lga_id"])


# --- Facilities ------------------------------------------------------------
class FacilityViewSet(viewsets.ModelViewSet):
    """List facilities (any authenticated user, for pickers/switchers) and
    create them (Systems admin only, via the State -> LGA -> Ward picker)."""

    queryset = Facility.objects.select_related(
        "ward__local_government__state"
    ).all()
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return FacilityCreateSerializer
        return FacilitySerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsSystemsAdmin()]
        return [IsAuthenticated()]


# --- Organisations ---------------------------------------------------------
class OrganisationViewSet(viewsets.ModelViewSet):
    """Systems-admin-only organisation management (05-api-routes.md)."""

    queryset = Organisation.objects.prefetch_related("facility_access", "users").all()
    serializer_class = OrganisationSerializer
    permission_classes = [IsSystemsAdmin]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        org = serializer.save(created_by=self.request.user)
        AuditEvent.objects.create(
            actor=self.request.user,
            event_type="organisation_created",
            subject_type="organisation",
            subject_id=org.id,
            metadata={"name": org.name},
        )

    @action(detail=True, methods=["post"], url_path="facility-access")
    def grant_access(self, request, pk=None):
        organisation = self.get_object()
        serializer = OrganisationFacilityAccessCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grant = OrganisationFacilityAccess.objects.create(
            organisation=organisation,
            scope_type=serializer.validated_data["scope_type"],
            scope_id=serializer.validated_data["scope_id"],
            access_level=serializer.validated_data["access_level"],
            granted_by=request.user,
        )
        AuditEvent.objects.create(
            actor=request.user,
            event_type="organisation_access_granted",
            subject_type="organisation",
            subject_id=organisation.id,
            metadata={
                "scope_type": grant.scope_type,
                "access_level": grant.access_level,
            },
        )
        return Response(
            OrganisationFacilityAccessSerializer(grant).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"facility-access/(?P<grant_id>[^/.]+)",
    )
    def revoke_access(self, request, pk=None, grant_id=None):
        organisation = self.get_object()
        grant = OrganisationFacilityAccess.objects.filter(
            organisation=organisation, pk=grant_id
        ).first()
        if grant is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        grant.delete()
        AuditEvent.objects.create(
            actor=request.user,
            event_type="organisation_access_revoked",
            subject_type="organisation",
            subject_id=organisation.id,
            metadata={"grant_id": str(grant_id)},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Users -----------------------------------------------------------------
class UserViewSet(viewsets.ModelViewSet):
    """Systems-admin user management. Create is live in Module 1 (needed to
    seat Facility leads, Data officers, and an organisation's first user);
    edit/deactivate/reactivate arrive with the /admin/users screen in Module 6.
    """

    queryset = User.objects.select_related("facility", "organisation").all()
    permission_classes = [IsSystemsAdmin]
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = serializer.save(created_by=self.request.user)
        AuditEvent.objects.create(
            actor=self.request.user,
            event_type="user_created",
            subject_type="user",
            subject_id=user.id,
            metadata={"role": user.role},
        )


class OrganisationUsersView(APIView):
    """GET/POST /organisations/{id}/users.

    List an organisation's own users, or invite a colleague into it. Creating
    a user here is allowed for a Systems admin OR an Organisation user with
    can_manage_org_users acting on their OWN organisation. Invited users are
    always role organisation_user (05-api-routes.md).
    """

    permission_classes = [IsAuthenticated]

    def _can_manage(self, request, organisation):
        user = request.user
        if user.role == Role.SYSTEMS_ADMIN:
            return True
        return bool(
            user.role == Role.ORGANISATION_USER
            and user.can_manage_org_users
            and user.organisation_id == organisation.id
        )

    def get(self, request, pk):
        organisation = Organisation.objects.filter(pk=pk).first()
        if organisation is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._can_manage(request, organisation):
            return Response(status=status.HTTP_403_FORBIDDEN)
        users = organisation.users.all()
        return Response(UserSerializer(users, many=True).data)

    @transaction.atomic
    def post(self, request, pk):
        organisation = Organisation.objects.filter(pk=pk).first()
        if organisation is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._can_manage(request, organisation):
            return Response(status=status.HTTP_403_FORBIDDEN)
        data = {
            "name": request.data.get("name"),
            "email": request.data.get("email"),
            "role": Role.ORGANISATION_USER,
            "organisation": organisation.id,
            "can_manage_org_users": bool(
                request.data.get("can_manage_org_users", False)
            ),
        }
        serializer = UserCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(created_by=request.user)
        AuditEvent.objects.create(
            actor=request.user,
            event_type="organisation_user_invited",
            subject_type="user",
            subject_id=user.id,
            facility=None,
            metadata={"organisation_id": str(organisation.id)},
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
