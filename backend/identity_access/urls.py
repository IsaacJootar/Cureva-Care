"""Identity & Access API routes (mounted under /api/v1/)."""
from django.urls import path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    FacilityViewSet,
    LocalGovernmentListView,
    MeView,
    OrganisationUsersView,
    OrganisationViewSet,
    StateListView,
    UserViewSet,
    WardListView,
)
from .views_auth import (
    GoogleCallbackView,
    GoogleStartView,
    MagicLinkRequestView,
    SessionExchangeView,
)

router = SimpleRouter(trailing_slash=False)
router.register("facilities", FacilityViewSet, basename="facility")
router.register("organisations", OrganisationViewSet, basename="organisation")
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    # Auth
    path("auth/magic-link", MagicLinkRequestView.as_view(), name="magic-link"),
    path("auth/session", SessionExchangeView.as_view(), name="session-exchange"),
    path("auth/google/start", GoogleStartView.as_view(), name="google-start"),
    path("auth/google/callback", GoogleCallbackView.as_view(), name="google-callback"),
    path("auth/token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    # Self
    path("users/me", MeView.as_view(), name="me"),
    # Geo pickers
    path("states", StateListView.as_view(), name="states"),
    path(
        "states/<uuid:state_id>/local-governments",
        LocalGovernmentListView.as_view(),
        name="state-lgas",
    ),
    path(
        "local-governments/<uuid:lga_id>/wards",
        WardListView.as_view(),
        name="lga-wards",
    ),
    # Organisation-scoped users (list/invite)
    path(
        "organisations/<uuid:pk>/users",
        OrganisationUsersView.as_view(),
        name="organisation-users",
    ),
]

urlpatterns += router.urls
