"""Reporting API — saved briefs + access-level-enforced, audited exports."""
import csv

from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from identity_access.models import AccessLevel
from identity_access.permissions import IsDashboardViewer
from intelligence.scoping import caller_scope
from intelligence.views import IDENTITY_FIELDS

from .generator import build_sections, generate_narrative
from .models import ExportAudit, SavedReport


class ReportsView(APIView):
    """GET /reports (list) and POST /reports (generate + save a brief)."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = set(caller_scope(request.user)["facility_ids"] or [])
        reports = SavedReport.objects.all()[:100]
        visible = [
            r for r in reports
            if set(map(str, r.facility_ids)).issubset({str(x) for x in scope}) or r.generated_by_id == request.user.id
        ]
        return Response([
            {
                "id": str(r.id), "title": r.title, "period_from": r.period_from, "period_to": r.period_to,
                "has_narrative": bool(r.narrative), "created_at": r.created_at,
            }
            for r in visible
        ])

    def post(self, request):
        scope = caller_scope(request.user)
        facility_ids = list(scope["facility_ids"] or [])
        date_from = request.data.get("from") or None
        date_to = request.data.get("to") or None
        with_narrative = bool(request.data.get("with_narrative", False))

        sections = build_sections(facility_ids, date_from, date_to)
        narrative = generate_narrative(sections) if with_narrative else None

        report = SavedReport.objects.create(
            title=request.data.get("title") or "Maternal care brief",
            facility_ids=[str(f) for f in facility_ids],
            period_from=date_from, period_to=date_to,
            sections=sections, narrative=narrative, generated_by=request.user,
        )
        ExportAudit.objects.create(
            exported_by=request.user, export_type="report",
            access_level=scope["access_level"], facility_ids=[str(f) for f in facility_ids],
        )
        return Response(_report_detail(report), status=201)


class ReportDetailView(APIView):
    permission_classes = [IsDashboardViewer]

    def get(self, request, report_id):
        report = SavedReport.objects.filter(pk=report_id).first()
        if report is None:
            return Response(status=404)
        scope = {str(x) for x in (caller_scope(request.user)["facility_ids"] or [])}
        if not set(report.facility_ids).issubset(scope) and report.generated_by_id != request.user.id:
            return Response(status=403)
        return Response(_report_detail(report))


def _report_detail(report):
    return {
        "id": str(report.id), "title": report.title,
        "period_from": report.period_from, "period_to": report.period_to,
        "sections": report.sections, "narrative": report.narrative,
        "created_at": report.created_at,
    }


class RecordsExportView(APIView):
    """GET /records/export — CSV of verified rows, scoped + access-level
    filtered + audited (cureva-docs/07). Aggregate tier gets no row export."""

    permission_classes = [IsDashboardViewer]

    def get(self, request):
        scope = caller_scope(request.user)
        if scope["access_level"] == AccessLevel.AGGREGATE:
            return Response({"detail": "Aggregate access does not include record exports."}, status=403)
        facility_ids = list(scope["facility_ids"] or [])
        de_identify = scope["access_level"] == AccessLevel.DE_IDENTIFIED

        from register_intake.models import SourceRow, SourceRowStatus

        rows = (
            SourceRow.objects.filter(intake__facility_id__in=facility_ids, status=SourceRowStatus.VERIFIED)
            .select_related("intake")
            .order_by("-intake__published_at")
        )

        # Collect field union.
        all_fields: list = []
        seen = set()
        materialised = []
        for r in rows:
            values = dict(r.normalized or {})
            if de_identify:
                for k in IDENTITY_FIELDS:
                    values.pop(k, None)
            materialised.append((r, values))
            for k in values:
                if k not in seen:
                    seen.add(k)
                    all_fields.append(k)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="cureva-records.csv"'
        writer = csv.writer(response)
        writer.writerow(["register_family", "service_date", *all_fields])
        for r, values in materialised:
            writer.writerow([r.intake.register_family, r.service_date or "", *[values.get(f, "") for f in all_fields]])

        ExportAudit.objects.create(
            exported_by=request.user, export_type="records_csv",
            access_level=scope["access_level"], facility_ids=[str(f) for f in facility_ids],
            row_count=len(materialised),
        )
        return response
