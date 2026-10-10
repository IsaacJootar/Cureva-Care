"""Role-based DRF permissions.

Access rules are enforced server-side, never by the frontend hiding a screen
(cureva-docs/05-api-routes.md, 07-security-privacy-access.md). Organisation
users are read-only at the API layer: every capture/correct/resolve endpoint
rejects them outright, with one narrow explicit exception (managing their own
organisation's users).
"""
from rest_framework.permissions import BasePermission

from .models import Role


class IsSystemsAdmin(BasePermission):
    message = "Systems admin role required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.SYSTEMS_ADMIN
        )


class IsDataOfficer(BasePermission):
    message = "Data officer role required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.DATA_OFFICER
        )


class IsFacilityLead(BasePermission):
    message = "Facility lead role required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.FACILITY_LEAD
        )


class IsOrganisationUser(BasePermission):
    message = "Organisation user role required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.ORGANISATION_USER
        )


class IsDashboardViewer(BasePermission):
    """Facility lead or Organisation user — the two roles that read dashboards.

    The shared dashboard/report endpoints use this; scope (one facility vs an
    organisation's granted set) is resolved separately, server-side.
    """

    message = "Dashboard access is limited to Facility leads and Organisation users."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {Role.FACILITY_LEAD, Role.ORGANISATION_USER}
        )
