"""Root URL configuration.

Django renders NO user-facing pages (cureva-docs/04-architecture-and-stack.md):
the entire product UI is the Next.js app. Django exposes only the versioned
REST API under /api/v1/. Django's built-in admin is intentionally NOT routed
in the shipped product.
"""
from django.http import JsonResponse
from django.urls import include, path


def healthz(_request):
    return JsonResponse({"status": "ok", "service": "cureva-care-api"})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("api/v1/", include("cureva.api_urls")),
]
