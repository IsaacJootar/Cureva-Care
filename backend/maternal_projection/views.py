"""Identity-review queue API — Facility lead only (cureva-docs/05).

A Facility lead is the only role that confirms/rejects candidate matches, and
only within their own assigned facility. Organisation users and others are
rejected.
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from identity_access.models import Role

from .identity import confirm_candidate, reject_candidate
from .models import CandidateStatus, IdentityCandidate
from .serializers import IdentityCandidateSerializer


def _facility_candidate(user, candidate_id):
    if user.role != Role.FACILITY_LEAD or not user.facility_id:
        return None
    return IdentityCandidate.objects.filter(pk=candidate_id, facility_id=user.facility_id).first()


class IdentityCandidatesView(APIView):
    """GET /identity-candidates — pending matches for the caller's facility."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != Role.FACILITY_LEAD or not user.facility_id:
            return Response(status=403)
        qs = (
            IdentityCandidate.objects.filter(
                facility_id=user.facility_id, status=CandidateStatus.PENDING
            )
            .select_related("source_row__intake", "candidate_woman")
        )
        return Response(IdentityCandidateSerializer(qs, many=True).data)


class ConfirmCandidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, candidate_id):
        candidate = _facility_candidate(request.user, candidate_id)
        if candidate is None:
            return Response(status=404)
        result = confirm_candidate(candidate, request.user)
        return Response(result)


class RejectCandidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, candidate_id):
        candidate = _facility_candidate(request.user, candidate_id)
        if candidate is None:
            return Response(status=404)
        result = reject_candidate(candidate, request.user)
        return Response(result)
