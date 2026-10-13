"""Versioned API surface (/api/v1/).

Each service-boundary app contributes its own routes. Apps are wired in as
their module is built, per cureva-docs/10-build-execution-checklist.md.
"""
from django.urls import include, path

urlpatterns = [
    path("", include("identity_access.urls")),
    path("", include("register_intake.urls")),
    path("", include("maternal_projection.urls")),
    path("", include("intelligence.urls")),
    path("", include("reporting.urls")),
]
