"""Reporting API routes (mounted under /api/v1/)."""
from django.urls import path

from .views import RecordsExportView, ReportDetailView, ReportsView

urlpatterns = [
    path("reports", ReportsView.as_view(), name="reports"),
    path("reports/<uuid:report_id>", ReportDetailView.as_view(), name="report-detail"),
    path("records/export", RecordsExportView.as_view(), name="records-export"),
]
