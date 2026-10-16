"""Intelligence API routes (mounted under /api/v1/)."""
from django.urls import path

from .views import (
    CareJourneyView,
    FacilitiesOverviewView,
    MaternalSummaryView,
    RecordsView,
    TrendsView,
    WorklistActionView,
    WorklistView,
    WorkspaceView,
)

urlpatterns = [
    path("workspace", WorkspaceView.as_view(), name="workspace"),
    path("maternal-summary", MaternalSummaryView.as_view(), name="maternal-summary"),
    path("trends", TrendsView.as_view(), name="trends"),
    path("care-journey", CareJourneyView.as_view(), name="care-journey"),
    path("facilities-overview", FacilitiesOverviewView.as_view(), name="facilities-overview"),
    path("records", RecordsView.as_view(), name="records"),
    path("worklists", WorklistView.as_view(), name="worklists"),
    path("worklists/<str:item_id>/action", WorklistActionView.as_view(), name="worklist-action"),
]
