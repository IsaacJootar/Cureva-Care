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

from identity_access.models import AuditEvent
from identity_access.permissions import IsFacilityLead

from .benchmarking import METRICS, equity_by_parity, facility_league, geo_rollup
from .continuum import DROPOFFS, care_funnel, cohort_retention, dropoff_lines
from .metrics import maternal_summary
from .surveillance import case_timeline, facility_clusters, severe_cases, severe_trend
from .models import WorklistAction
from .rules import evaluate_worklist
from .scoping import caller_scope
from .trends import compute_trends

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


class TrendsView(APIView):
    """GET /trends — time-bucketed metric series (WS1), scoped to the caller.
    Query: from, to (service dates), bucket=month|week."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        bucket = request.query_params.get("bucket", "month")
        data = compute_trends(scope["facility_ids"], date_from, date_to, bucket)
        data["access_level"] = scope["access_level"]
        return Response(data)


class BenchmarkingView(APIView):
    """GET /benchmarking — facility league table on a chosen metric (WS2)."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        metric = request.query_params.get("metric", "deliveries")
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = facility_league(scope["facility_ids"], metric, date_from, date_to)
        data["available_metrics"] = [{"key": k, **v} for k, v in METRICS.items()]
        data["access_level"] = scope["access_level"]
        return Response(data)


class GeoRollupView(APIView):
    """GET /geo — a metric aggregated to State or LGA for the geographic view."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        metric = request.query_params.get("metric", "deliveries")
        level = request.query_params.get("level", "state")
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = geo_rollup(scope["facility_ids"], metric, level, date_from, date_to)
        data["access_level"] = scope["access_level"]
        return Response(data)


class EquityView(APIView):
    """GET /equity — ANC coverage sliced by recorded parity band (WS2)."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = equity_by_parity(scope["facility_ids"], date_from, date_to)
        data["access_level"] = scope["access_level"]
        return Response(data)


class ContinuumFunnelView(APIView):
    """GET /continuum/funnel — care-journey funnel with drop-offs (WS3)."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = care_funnel(scope["facility_ids"], date_from, date_to)
        data["access_level"] = scope["access_level"]
        return Response(data)


class DropoffView(APIView):
    """GET /continuum/dropoff?kind= — access-scoped line-list of women who fell
    out at a step. Aggregate tier gets counts only (never the women)."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        kind = request.query_params.get("kind", "delivered_no_pnc")
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = dropoff_lines(scope["facility_ids"], kind, scope["access_level"], date_from, date_to)
        data["available_kinds"] = [{"key": k, "label": v} for k, v in DROPOFFS.items()]
        return Response(data)


class CohortView(APIView):
    """GET /continuum/cohorts — booking-month cohort retention (WS3)."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = cohort_retention(scope["facility_ids"], date_from, date_to)
        data["access_level"] = scope["access_level"]
        return Response(data)


class SurveillanceCasesView(APIView):
    """GET /surveillance/cases — MPDSR severe-outcome case register (WS4),
    access-scoped (aggregate tier gets counts only)."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        return Response(severe_cases(scope["facility_ids"], scope["access_level"], date_from, date_to))


class CaseTimelineView(APIView):
    """GET /surveillance/cases/{episode_id} — one woman's linked ANC→Delivery→PNC
    story. Blocked for aggregate-tier callers (case-level data)."""

    permission_classes = [IsDashboardViewer]

    def get(self, request, episode_id):
        scope = caller_scope(request.user)
        if scope["access_level"] == AccessLevel.AGGREGATE:
            return Response({"detail": "Aggregate access does not include case-level timelines."}, status=403)
        return Response(case_timeline(episode_id, scope["facility_ids"], scope["access_level"]))


class SevereTrendView(APIView):
    """GET /surveillance/trend — severe outcomes over time by type (WS4)."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        return Response(severe_trend(scope["facility_ids"], date_from, date_to))


class ClustersView(APIView):
    """GET /surveillance/clusters — per-facility severe-outcome rate, ranked."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        return Response(facility_clusters(scope["facility_ids"], date_from, date_to))


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


class WorklistView(APIView):
    """GET /worklists — Facility-lead-only (cureva-docs/05 "Notes for
    implementation"). An Organisation user caller is rejected outright — this
    is a read restriction, not just a filter. Each item carries its triggering
    rule, severity, and any follow-up action history; an actioned item that is
    still true resurfaces (cureva-docs/02)."""

    permission_classes = [IsFacilityLead]

    def get(self, request):
        facility_id = request.user.facility_id
        items = evaluate_worklist([facility_id])
        # Attach the latest follow-up action per item, if any.
        for item in items:
            last = (
                WorklistAction.objects.filter(
                    rule_key=item["rule_key"], subject_id=item["subject_id"]
                )
                .select_related("actioned_by")
                .order_by("-actioned_at")
                .first()
            )
            item["last_actioned"] = (
                {
                    "by": last.actioned_by.name,
                    "at": last.actioned_at,
                    "note": last.note,
                }
                if last
                else None
            )
        return Response({"items": items})


class WorklistActionView(APIView):
    """POST /worklists/{itemId}/action — Facility lead records a follow-up. An
    audit overlay only: never edits the register data or referral_status."""

    permission_classes = [IsFacilityLead]

    def post(self, request, item_id):
        try:
            rule_key, subject_id = item_id.split(":", 1)
        except ValueError:
            return Response({"detail": "Malformed item id."}, status=400)
        action = WorklistAction.objects.create(
            rule_key=rule_key,
            subject_type=request.data.get("subject_type", ""),
            subject_id=subject_id,
            facility_id=request.user.facility_id,
            note=request.data.get("note") or None,
            actioned_by=request.user,
        )
        AuditEvent.objects.create(
            actor=request.user, event_type="worklist_actioned",
            subject_type="worklist_action", subject_id=action.id,
            facility_id=request.user.facility_id, metadata={"rule_key": rule_key},
        )
        return Response({"status": "actioned", "actioned_at": action.actioned_at}, status=201)


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
