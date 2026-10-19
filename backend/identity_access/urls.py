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
    ChangePasswordView,
    MagicLinkRequestView,
    PasswordLoginView,
    SessionExchangeView,
)
from .views_ops import (
    NotificationPreferenceUpdateView,
    NotificationPreferencesView,
    OrgUserDeleteView,
    SettingUpdateView,
    SettingsListView,
    TierUpdateView,
    TiersView,
    UserDeactivateView,
    UserFacilityView,
    UserReactivateView,
    UserSetPasswordView,
)

router = SimpleRouter(trailing_slash=False)
router.register("facilities", FacilityViewSet, basename="facility")
router.register("organisations", OrganisationViewSet, basename="organisation")
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    # Auth
    path("auth/login", PasswordLoginView.as_view(), name="password-login"),
    path("auth/change-password", ChangePasswordView.as_view(), name="change-password"),
    path("auth/magic-link", MagicLinkRequestView.as_view(), name="magic-link"),
    path("auth/session", SessionExchangeView.as_view(), name="session-exchange"),
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
    # Organisation-scoped users (list/invite/deactivate)
    path(
        "organisations/<uuid:pk>/users",
        OrganisationUsersView.as_view(),
        name="organisation-users",
    ),
    path(
        "organisations/<uuid:pk>/users/<uuid:user_id>",
        OrgUserDeleteView.as_view(),
        name="organisation-user-delete",
    ),
    # Platform settings
    path("tiers", TiersView.as_view(), name="tiers"),
    path("tiers/<uuid:tier_id>", TierUpdateView.as_view(), name="tier-update"),
    path("settings", SettingsListView.as_view(), name="settings"),
    path("settings/<str:key>", SettingUpdateView.as_view(), name="setting-update"),
    # Notification preferences (self-service)
    path("users/<uuid:user_id>/notification-preferences", NotificationPreferencesView.as_view(), name="notification-prefs"),
    path("users/<uuid:user_id>/notification-preferences/<str:notification_type>", NotificationPreferenceUpdateView.as_view(), name="notification-pref-update"),
    # User management
    path("users/<uuid:user_id>/deactivate", UserDeactivateView.as_view(), name="user-deactivate"),
    path("users/<uuid:user_id>/set-password", UserSetPasswordView.as_view(), name="user-set-password"),
    path("users/<uuid:user_id>/reactivate", UserReactivateView.as_view(), name="user-reactivate"),
    path("users/<uuid:user_id>/facility", UserFacilityView.as_view(), name="user-facility"),
]

urlpatterns += router.urls
