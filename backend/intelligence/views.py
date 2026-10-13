"""Dashboard/reporting API — the shared surface for Facility leads and
Organisation users (cureva-docs/05). Scope is resolved server-side on every
request (never trusted from the client); the same code path serves both roles,
only the resolved facility set and access tier differ.
"""
from datetime import date, timedelta

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from identity_access.models import AccessLevel, Facility, Role
from identity_access.permissions import IsDashboardViewer
from identity_access.services import get_setting
from identity_access.settings_registry import STALE_FACILITY_ALERT_DAYS

from .metrics import maternal_summary
from .scoping import caller_scope

IDENTITY_FIELDS = {"card_number", "name", "woman_name", "phone", "cl_phone"}


def _parse_date(s):
    try:
        return date.fromisoformat(s) if s else None
    except (ValueError, TypeError):
        return None


class MaternalSummaryView(APIView):
    """GET /maternal-summary — deterministic maternal metrics for a service-date
    window, scoped to the caller."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        summary = maternal_summary(scope["facility_ids"], date_from, date_to)
        summary["access_level"] = scope["access_level"]
        return Response(summary)


class CareJourneyView(APIView):
    """GET /care-journey — the care-journey funnel + linkage, scoped."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        summary = maternal_summary(scope["facility_ids"], date_from, date_to)
        return Response({"care_journey": summary["care_journey"], "metrics": summary["metrics"]})


class WorkspaceView(APIView):
    """GET /workspace — first-paint context: the caller's scope, their
    facilities, and headline counts in one call."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        facility_ids = list(scope["facility_ids"] or [])
        facilities = Facility.objects.filter(id__in=facility_ids).select_related(
            "ward__local_government__state"
        )
        summary = maternal_summary(facility_ids)
        return Response({
            "role": request.user.role,
            "access_level": scope["access_level"],
            "facility_count": len(facility_ids),
            "facilities": [
                {
                    "id": str(f.id),
                    "name": f.name,
                    "region": f"{f.state.name} · {f.local_government.name}",
                }
                for f in facilities
            ],
            "summary": summary,
        })


class FacilitiesOverviewView(APIView):
    """GET /facilities-overview — per-facility rows for the Facilities dashboard
    (reporting freshness, verified records, open referrals, stale flag)."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        facility_ids = list(scope["facility_ids"] or [])
        stale_days = int(get_setting(STALE_FACILITY_ALERT_DAYS))
        cutoff = timezone.now() - timedelta(days=stale_days)

        rows = []
        facilities = Facility.objects.filter(id__in=facility_ids).select_related(
            "ward__local_government__state"
        )
        for f in facilities:
            from register_intake.models import Intake, IntakeStatus

            last = (
                Intake.objects.filter(facility=f, status=IntakeStatus.PUBLISHED)
                .order_by("-published_at")
                .values_list("published_at", flat=True)
                .first()
            )
            summ = maternal_summary([f.id])
            rows.append({
                "id": str(f.id),
                "name": f.name,
                "region": f"{f.state.name} · {f.local_government.name}",
                "last_intake": last,
                "is_stale": (last is None) or (last < cutoff),
                "verified_records": summ["operational"]["verified_records"],
                "open_referrals": summ["operational"]["open_referrals"],
                "deliveries": summ["operational"]["deliveries"],
            })
        return Response({"facilities": rows, "stale_days": stale_days})


class RecordsView(APIView):
    """GET /records — paginated verified rows, scoped and access-level filtered.
    Aggregate-tier callers get no row-level detail (counts only); de-identified
    strips declared identity fields; identifiable sees full evidence."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        if scope["access_level"] == AccessLevel.AGGREGATE:
            return Response(
                {"detail": "Aggregate access does not include row-level records."},
                status=403,
            )
        facility_ids = list(scope["facility_ids"] or [])
        de_identify = scope["access_level"] == AccessLevel.DE_IDENTIFIED

        from register_intake.models import SourceRow, SourceRowStatus

        qs = (
            SourceRow.objects.filter(
                intake__facility_id__in=facility_ids, status=SourceRowStatus.VERIFIED
            )
            .select_related("intake")
            .order_by("-intake__published_at", "row_number")
        )
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1
        page_size = 25
        total = qs.count()
        rows = qs[(page - 1) * page_size : page * page_size]

        results = []
        for r in rows:
            values = dict(r.normalized or {})
            if de_identify:
                for k in IDENTITY_FIELDS:
                    values.pop(k, None)
            results.append({
                "id": str(r.id),
                "register_family": r.intake.register_family,
                "service_date": r.service_date,
                "facility_id": str(r.intake.facility_id),
                "values": values,
                "flags": r.flags,
            })
        return Response({
            "results": results,
            "count": total,
            "page": page,
            "page_size": page_size,
            "access_level": scope["access_level"],
        })
