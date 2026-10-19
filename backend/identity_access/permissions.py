"""Role-based DRF permissions.

Access rules are enforced server-side, never by the frontend hiding a screen
(cureva-docs/05-api-routes.md, 07-security-privacy-access.md). Organisation
users are read-only at the API layer: every capture/correct/resolve endpoint
rejects them outright, with one narrow explicit exception (managing their own
organisation's users).
"""
from rest_framework.permissions import BasePermission

from .entitlements import has_module, module_for_path
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


class HasModule(BasePermission):
    """Gate an intelligence endpoint by the module an organisation subscribed to.

    The module is resolved from the request path (identity_access.entitlements).
    A path that maps to no module is ungated (e.g. /workspace). Enforced
    server-side — hiding a sidebar link is not enough (11-intelligence-module.md).
    """

    message = "Your subscription does not include this intelligence module."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return has_module(request.user, module_for_path(request.path))
