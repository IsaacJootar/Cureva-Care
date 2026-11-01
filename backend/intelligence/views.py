"""Dashboard/reporting API — the shared surface for Facility leads and
Organisation users (cureva-docs/05). Scope is resolved server-side on every
request (never trusted from the client); the same code path serves both roles,
only the resolved facility set and access tier differ.
"""
from datetime import date, timedelta

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from identity_access.models import AccessLevel, Facility, LocalGovernment, Role
from identity_access.permissions import HasModule, IsDashboardViewer, IsSystemsAdmin
from identity_access.services import get_setting
from identity_access.settings_registry import STALE_FACILITY_ALERT_DAYS

from identity_access.models import AuditEvent
from identity_access.permissions import IsFacilityLead

from .benchmarking import METRICS, equity_by_parity, facility_league, geo_rollup
from .coverage import INDICATORS as COVERAGE_INDICATORS, coverage
from .early_warning import early_warnings
from .equity import equity_breakdown
from .mpdsr import CAUSE_LABEL, FACTOR_LABEL, mpdsr_summary, review_queue
from .models import DeathReview
from .quality import quality_scorecard
from .referrals import referrals_summary
from .targets import TARGET_CATALOGUE, target_progress
from .models import CoverageDenominator, ProgramTarget
from .alerts import evaluate_alerts
from .continuum import DROPOFFS, care_funnel, cohort_retention, dropoff_lines
from .metrics import maternal_summary
from .rdqa import rdqa_scorecard, rdqa_trend
from .risk import risk_pyramid, risk_registry
from .surveillance import case_timeline, facility_clusters, severe_cases, severe_trend
from .models import WorklistAction
from .rules import evaluate_worklist
from .scoping import caller_scope, resolve_scope, scope_options
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

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        summary = maternal_summary(scope["facility_ids"], date_from, date_to)
        summary["access_level"] = scope["access_level"]
        return Response(summary)


class CareJourneyView(APIView):
    """GET /care-journey — the care-journey funnel + linkage, scoped."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        summary = maternal_summary(scope["facility_ids"], date_from, date_to)
        return Response({"care_journey": summary["care_journey"], "metrics": summary["metrics"]})


class TrendsView(APIView):
    """GET /trends — time-bucketed metric series (WS1), scoped to the caller.
    Query: from, to (service dates), bucket=month|week."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        bucket = request.query_params.get("bucket", "month")
        data = compute_trends(scope["facility_ids"], date_from, date_to, bucket)
        data["access_level"] = scope["access_level"]
        return Response(data)


class BenchmarkingView(APIView):
    """GET /benchmarking — facility league table on a chosen metric (WS2)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        metric = request.query_params.get("metric", "deliveries")
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = facility_league(scope["facility_ids"], metric, date_from, date_to)
        data["available_metrics"] = [{"key": k, **v} for k, v in METRICS.items()]
        data["access_level"] = scope["access_level"]
        return Response(data)


class GeoRollupView(APIView):
    """GET /geo — a metric aggregated to State or LGA for the geographic view."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        metric = request.query_params.get("metric", "deliveries")
        level = request.query_params.get("level", "state")
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = geo_rollup(scope["facility_ids"], metric, level, date_from, date_to)
        data["access_level"] = scope["access_level"]
        return Response(data)


class EquityView(APIView):
    """GET /equity — ANC coverage sliced by recorded parity band (WS2)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = equity_by_parity(scope["facility_ids"], date_from, date_to)
        data["access_level"] = scope["access_level"]
        return Response(data)


class ContinuumFunnelView(APIView):
    """GET /continuum/funnel — care-journey funnel with drop-offs (WS3)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = care_funnel(scope["facility_ids"], date_from, date_to)
        data["access_level"] = scope["access_level"]
        return Response(data)


class DropoffView(APIView):
    """GET /continuum/dropoff?kind= — access-scoped line-list of women who fell
    out at a step. Aggregate tier gets counts only (never the women)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        kind = request.query_params.get("kind", "delivered_no_pnc")
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = dropoff_lines(scope["facility_ids"], kind, scope["access_level"], date_from, date_to)
        data["available_kinds"] = [{"key": k, "label": v} for k, v in DROPOFFS.items()]
        return Response(data)


class CohortView(APIView):
    """GET /continuum/cohorts — booking-month cohort retention (WS3)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = cohort_retention(scope["facility_ids"], date_from, date_to)
        data["access_level"] = scope["access_level"]
        return Response(data)


class SurveillanceCasesView(APIView):
    """GET /surveillance/cases — MPDSR severe-outcome case register (WS4),
    access-scoped (aggregate tier gets counts only)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        return Response(severe_cases(scope["facility_ids"], scope["access_level"], date_from, date_to))


class CaseTimelineView(APIView):
    """GET /surveillance/cases/{episode_id} — one woman's linked ANC→Delivery→PNC
    story. Blocked for aggregate-tier callers (case-level data)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request, episode_id):
        scope = resolve_scope(request.user, request)
        if scope["access_level"] == AccessLevel.AGGREGATE:
            return Response({"detail": "Aggregate access does not include case-level timelines."}, status=403)
        return Response(case_timeline(episode_id, scope["facility_ids"], scope["access_level"]))


class SevereTrendView(APIView):
    """GET /surveillance/trend — severe outcomes over time by type (WS4)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        return Response(severe_trend(scope["facility_ids"], date_from, date_to))


class ClustersView(APIView):
    """GET /surveillance/clusters — per-facility severe-outcome rate, ranked."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        return Response(facility_clusters(scope["facility_ids"], date_from, date_to))


class RiskPyramidView(APIView):
    """GET /risk/pyramid — active-pregnancy risk-tier distribution (WS5)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        data = risk_pyramid(scope["facility_ids"])
        data["facility_count"] = len(scope["facility_ids"] or [])
        return Response(data)


class RiskRegistryView(APIView):
    """GET /risk/registry — active high/moderate-risk pregnancies, access-scoped."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        tier = request.query_params.get("tier")
        return Response(risk_registry(scope["facility_ids"], scope["access_level"], tier))


class AlertsView(APIView):
    """GET /alerts — early-warning alerts for the caller's scope (WS5)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        return Response({"alerts": evaluate_alerts(scope["facility_ids"])})


class RDQAScorecardView(APIView):
    """GET /rdqa/scorecard — continuous data-quality assessment per facility (WS6)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        return Response(rdqa_scorecard(scope["facility_ids"], date_from, date_to))


class RDQATrendView(APIView):
    """GET /rdqa/trend — mean extraction confidence over time (WS6)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        return Response(rdqa_trend(scope["facility_ids"]))


class WorkspaceView(APIView):
    """GET /workspace — first-paint context: the caller's scope, their
    facilities, and headline counts in one call."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        facility_ids = list(scope["facility_ids"] or [])
        facilities = Facility.objects.filter(id__in=facility_ids).select_related(
            "ward__local_government__state"
        )
        summary = maternal_summary(facility_ids)
        facilities = list(facilities)
        # Facility-first scope: how many facilities, and across how many wards /
        # LGAs / states they sit (the hierarchy the customer is buying into).
        wards = {f.ward_id for f in facilities}
        lgas = {f.ward.local_government_id for f in facilities}
        states = {f.ward.local_government.state_id for f in facilities}
        return Response({
            "role": request.user.role,
            "access_level": scope["access_level"],
            "facility_count": len(facility_ids),
            "scope_breakdown": {
                "facilities": len(facilities),
                "wards": len(wards),
                "lgas": len(lgas),
                "states": len(states),
            },
            "facilities": [
                {
                    "id": str(f.id),
                    "name": f.name,
                    "region": f.region_path,
                    "ward": f.ward.name,
                    "lga": f.ward.local_government.name,
                    "state": f.ward.local_government.state.name,
                }
                for f in facilities
            ],
            "summary": summary,
        })


class FacilitiesOverviewView(APIView):
    """GET /facilities-overview — per-facility rows for the Facilities dashboard
    (reporting freshness, verified records, open referrals, stale flag)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
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
                "region": f.region_path,
                "ward": f.ward.name,
                "lga": f.ward.local_government.name,
                "state": f.ward.local_government.state.name,
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

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
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


# --- Coverage & Reach (expansion M1) ---------------------------------------
class CoverageView(APIView):
    """GET /coverage — recorded activity as a share of expected (population
    estimate). Query: year, level=lga|state, indicator=anc1|anc4|sba|pnc,
    from, to. Scoped to the caller; every figure is an estimate (sources
    returned), and areas without a loaded denominator get no rate."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        try:
            year = int(request.query_params.get("year") or date.today().year)
        except (TypeError, ValueError):
            year = date.today().year
        level = request.query_params.get("level", "lga")
        indicator = request.query_params.get("indicator", "anc1")
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = coverage(scope["facility_ids"], year, level, indicator, date_from, date_to)
        data["indicator_catalogue"] = [
            {"key": k, "label": v["label"]} for k, v in COVERAGE_INDICATORS.items()
        ]
        data["access_level"] = scope["access_level"]
        return Response(data)


class CoverageDenominatorsView(APIView):
    """Systems-admin: load/list the population denominators that power coverage.

    GET /coverage/denominators?year= — every LGA that has a facility, with its
    current expected pregnancies/births for the year (blank where not loaded).
    POST — upsert one LGA's estimate for the year.
    """

    permission_classes = [IsSystemsAdmin]

    def get(self, request):
        try:
            year = int(request.query_params.get("year") or date.today().year)
        except (TypeError, ValueError):
            year = date.today().year
        lgas = (
            LocalGovernment.objects.filter(wards__facilities__isnull=False)
            .select_related("state")
            .distinct()
            .order_by("state__name", "name")
        )
        existing = {
            str(d.area_id): d
            for d in CoverageDenominator.objects.filter(
                area_type=CoverageDenominator.AreaType.LOCAL_GOVERNMENT, year=year
            )
        }
        rows = []
        for lga in lgas:
            d = existing.get(str(lga.id))
            rows.append({
                "area_type": "local_government",
                "area_id": str(lga.id),
                "name": lga.name,
                "state_name": lga.state.name,
                "expected_pregnancies": d.expected_pregnancies if d else None,
                "expected_births": d.expected_births if d else None,
                "source": d.source if d else "",
            })
        return Response({"year": year, "rows": rows})

    def post(self, request):
        data = request.data
        area_id = data.get("area_id")
        try:
            year = int(data.get("year"))
        except (TypeError, ValueError):
            return Response({"detail": "A valid year is required."}, status=400)
        if not LocalGovernment.objects.filter(pk=area_id).exists():
            return Response({"detail": "Unknown LGA."}, status=400)

        def _int_or_none(v):
            if v in (None, ""):
                return None
            try:
                return max(0, int(v))
            except (TypeError, ValueError):
                return None

        row, _ = CoverageDenominator.objects.update_or_create(
            area_type=CoverageDenominator.AreaType.LOCAL_GOVERNMENT,
            area_id=area_id,
            year=year,
            defaults={
                "expected_pregnancies": _int_or_none(data.get("expected_pregnancies")),
                "expected_births": _int_or_none(data.get("expected_births")),
                "source": (data.get("source") or "").strip()[:160],
                "updated_by": request.user,
            },
        )
        AuditEvent.objects.create(
            actor=request.user, event_type="coverage_denominator_updated",
            subject_type="coverage_denominator", subject_id=row.id,
            metadata={"area_id": str(area_id), "year": year},
        )
        return Response({
            "area_id": str(area_id), "year": year,
            "expected_pregnancies": row.expected_pregnancies,
            "expected_births": row.expected_births, "source": row.source,
        }, status=200)


# --- Goals & Targets (expansion M7) ----------------------------------------
class GoalsView(APIView):
    """GET /goals — progress against the active program targets, scoped."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = target_progress(scope["facility_ids"], date_from, date_to)
        data["access_level"] = scope["access_level"]
        return Response(data)


class TargetsView(APIView):
    """Systems admin: GET the catalogue + every target's percentage, PATCH one.

    GET /targets — all indicators with their current target % and active flag.
    PATCH /targets/{key} — set target_pct / is_active for one indicator.
    """

    permission_classes = [IsSystemsAdmin]

    def get(self, request, key=None):
        existing = {t.key: t for t in ProgramTarget.objects.all()}
        rows = []
        for key, spec in TARGET_CATALOGUE.items():
            t = existing.get(key)
            rows.append({
                "key": key,
                "label": spec["label"],
                "help": spec["help"],
                "target_pct": t.target_pct if t else 0,
                "is_active": t.is_active if t else False,
                "order": t.order if t else 0,
            })
        rows.sort(key=lambda r: (r["order"], r["label"]))
        return Response({"targets": rows})

    def patch(self, request, key):
        if key not in TARGET_CATALOGUE:
            return Response({"detail": "Unknown target."}, status=404)
        t, _ = ProgramTarget.objects.get_or_create(key=key)
        if "target_pct" in request.data:
            try:
                t.target_pct = max(0, min(100, int(request.data["target_pct"])))
            except (TypeError, ValueError):
                return Response({"detail": "target_pct must be 0–100."}, status=400)
        if "is_active" in request.data:
            t.is_active = bool(request.data["is_active"])
        t.save()
        AuditEvent.objects.create(
            actor=request.user, event_type="program_target_updated",
            subject_type="program_target", subject_id=t.id,
            metadata={"key": key, "target_pct": t.target_pct, "is_active": t.is_active},
        )
        return Response({"key": key, "target_pct": t.target_pct, "is_active": t.is_active})


# --- Scope selector options (shared across dashboards) ----------------------
class ScopeOptionsView(APIView):
    """GET /scope-options — the facilities (and their states) the caller may view,
    to populate the dashboard scope selector."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        return Response(scope_options(request.user))


# --- Equity (expansion M6) --------------------------------------------------
class EquityBreakdownView(APIView):
    """GET /equity-breakdown — a coverage metric sliced by sub-group (past
    births / age / area) with the equity gap, scoped to the caller."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        dimension = request.query_params.get("dimension", "parity")
        metric = request.query_params.get("metric", "screening")
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = equity_breakdown(scope["facility_ids"], dimension, metric, date_from, date_to)
        data["access_level"] = scope["access_level"]
        return Response(data)


# --- Quality of care (expansion M4) -----------------------------------------
class QualityView(APIView):
    """GET /quality — WHO-essential care standards: share done, overall score,
    per-facility score, and the ranked gaps to fix. Scoped to the caller."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = quality_scorecard(scope["facility_ids"], date_from, date_to)
        data["access_level"] = scope["access_level"]
        return Response(data)


# --- Referral pathways & outcomes (expansion M5) ----------------------------
class ReferralsView(APIView):
    """GET /referrals — did referred women arrive and what happened; where the
    loop breaks down; which facilities close it. Scoped to the caller."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = referrals_summary(scope["facility_ids"], date_from, date_to)
        data["access_level"] = scope["access_level"]
        # Woman-level "went nowhere" list only for de-identified+ access.
        if scope["access_level"] == AccessLevel.AGGREGATE:
            data["lost"] = []
        return Response(data)


# --- Death reviews / MPDSR (expansion M2) -----------------------------------
class MpdsrSummaryView(APIView):
    """GET /mpdsr — aggregate review status: how many deaths reviewed, how many
    avoidable, what keeps contributing, whether actions get done. Safe for orgs
    (aggregates only; no woman-level data)."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        data = mpdsr_summary(scope["facility_ids"], date_from, date_to)
        level = scope["access_level"]
        data["access_level"] = level
        # Actions tracker: aggregate access gets counts only (no list); de-identified
        # sees the list without the woman's identity; identifiable (the facility's
        # own lead) sees her name.
        if level == AccessLevel.AGGREGATE:
            data["actions_list"] = []
        elif level == AccessLevel.DE_IDENTIFIED:
            for a in data.get("actions_list", []):
                a["woman_name"] = None
                a["woman_internal_id"] = None
        return Response(data)


class MpdsrQueueView(APIView):
    """GET /mpdsr/queue — the deaths to review and their review state. Facility
    lead only (woman-level, their own facility)."""

    permission_classes = [IsFacilityLead, HasModule]

    def get(self, request):
        fids = [request.user.facility_id] if request.user.facility_id else []
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        return Response(review_queue(fids, date_from, date_to))


class MpdsrReviewView(APIView):
    """PUT /mpdsr/reviews/{birth_event_id} — create/update one death's review.
    Facility lead only, and only for a death in their own facility."""

    permission_classes = [IsFacilityLead]

    def put(self, request, birth_event_id):
        from maternal_projection.models import BirthEvent

        b = BirthEvent.objects.filter(pk=birth_event_id).first()
        if b is None:
            return Response(status=404)
        if str(b.facility_id) != str(request.user.facility_id):
            return Response({"detail": "You can only review deaths in your own facility."}, status=403)

        d = request.data
        cause = (d.get("cause") or "").strip()
        if cause and cause not in CAUSE_LABEL:
            return Response({"detail": "Unknown cause."}, status=400)
        avoidable = d.get("avoidable") or DeathReview.Avoidable.UNKNOWN
        if avoidable not in DeathReview.Avoidable.values:
            return Response({"detail": "Unknown avoidability."}, status=400)
        factors = d.get("factors") or []
        if not isinstance(factors, list) or any(f not in FACTOR_LABEL for f in factors):
            return Response({"detail": "Unknown contributing factor."}, status=400)
        action_status = d.get("action_status") or DeathReview.ActionStatus.OPEN
        if action_status not in DeathReview.ActionStatus.values:
            return Response({"detail": "Unknown action status."}, status=400)

        review, _ = DeathReview.objects.update_or_create(
            birth_event=b,
            defaults={
                "facility_id": b.facility_id,
                "cause": cause,
                "avoidable": avoidable,
                "factors": factors,
                "notes": (d.get("notes") or "").strip(),
                "action": (d.get("action") or "").strip(),
                "action_owner": (d.get("action_owner") or "").strip()[:120],
                "action_status": action_status,
                "reviewed_by": request.user,
                "reviewed_at": timezone.now(),
            },
        )
        AuditEvent.objects.create(
            actor=request.user, event_type="death_review_saved",
            subject_type="death_review", subject_id=review.id,
            metadata={"avoidable": avoidable, "birth_event_id": str(birth_event_id)},
        )
        return Response({"status": "saved"})


# --- Early warning (expansion M3) -------------------------------------------
class EarlyWarningView(APIView):
    """GET /early-warning — a watch list of facilities whose numbers are heading
    the wrong way (falling activity, rising deaths, reporting gone quiet). Simple,
    explainable trends — a prompt to look, not a verdict. Scoped to the caller."""

    permission_classes = [IsDashboardViewer, HasModule]

    def get(self, request):
        scope = resolve_scope(request.user, request)
        data = early_warnings(scope["facility_ids"])
        data["access_level"] = scope["access_level"]
        return Response(data)
