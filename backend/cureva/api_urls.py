"""Versioned API surface (/api/v1/).

Each service-boundary app contributes its own routes. Apps are wired in as
their module is built, per cureva-docs/10-build-execution-checklist.md.
"""
from django.urls import include, path

urlpatterns = [
    path("", include("identity_access.urls")),
    path("", include("register_intake.urls")),
    # maternal_projection / intelligence / reporting routes are added in
    # their respective modules.
]
