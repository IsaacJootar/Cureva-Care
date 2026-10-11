"""Maternal Projection API routes (mounted under /api/v1/)."""
from django.urls import path

from .views import ConfirmCandidateView, IdentityCandidatesView, RejectCandidateView

urlpatterns = [
    path("identity-candidates", IdentityCandidatesView.as_view(), name="identity-candidates"),
    path("identity-candidates/<uuid:candidate_id>/confirm", ConfirmCandidateView.as_view(), name="identity-confirm"),
    path("identity-candidates/<uuid:candidate_id>/reject", RejectCandidateView.as_view(), name="identity-reject"),
]
