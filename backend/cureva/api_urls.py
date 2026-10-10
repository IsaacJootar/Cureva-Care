"""Versioned API surface (/api/v1/).

Each service-boundary app contributes its own routes. Apps are wired in as
their module is built, per cureva-docs/10-build-execution-checklist.md.
"""
from django.urls import include, path

urlpatterns = [
    # identity_access routes are wired in with the auth/API commit.
    # register_intake / maternal_projection / intelligence / reporting
    # routes are added in their respective modules.
]
