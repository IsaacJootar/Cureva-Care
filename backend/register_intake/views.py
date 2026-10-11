"""Register Intake API.

A Data officer's whole surface is the intake pipeline, scoped to their own
submitted batches. Field confirmation is also reachable by a Facility lead for
their facility's batches. Template mapping is Systems-admin only. Organisation
users are rejected on every endpoint here (cureva-docs/05, 07).
"""
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from identity_access.models import AuditEvent, Facility, Role
from identity_access.permissions import IsDataOfficer, IsSystemsAdmin

from . import storage
from .models import (
    Intake,
    IntakeImage,
    RegisterMismatchStatus,
    SourceRow,
    Template,
    TemplateFlag,
)
from .pipeline import process_intake, resolve_register_mismatch
from .publish import PublishError, confirm_field, publish_intake
from .resolution import compute_page_hash, compute_source_hash
from .serializers import (
    IntakeSerializer,
    SourceRowSerializer,
    TemplateFlagSerializer,
    TemplateSerializer,
)


def _get_intake_for_officer(request, intake_id):
    return Intake.objects.filter(pk=intake_id, submitted_by=request.user).first()


class IntakeCreateView(APIView):
    """POST /intakes — data officer stages a batch (one or more register-page
    images) against a chosen facility. A duplicate checksum is a no-op."""

    permission_classes = [IsDataOfficer]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        facility_id = request.data.get("facility")
        register_family = request.data.get("register_family")
        period_from = request.data.get("batch_period_from")
        period_to = request.data.get("batch_period_to")
        files = request.FILES.getlist("images")

        if not (facility_id and register_family and period_from and period_to):
            return Response({"detail": "facility, register_family, and batch period are required."}, status=400)
        if not files:
            return Response({"detail": "At least one register-page image is required."}, status=400)
        if not Facility.objects.filter(pk=facility_id).exists():
            return Response({"detail": "Unknown facility."}, status=400)

        page_bytes = [f.read() for f in files]
        source_hash = compute_source_hash(page_bytes)

        existing = Intake.objects.filter(
            facility_id=facility_id, register_family=register_family, source_hash=source_hash
        ).first()
        if existing:
            # Idempotent: duplicate file upload is a no-op, not a re-import.
            return Response(
                {"detail": "Duplicate batch — already submitted.", **IntakeSerializer(existing).data},
                status=status.HTTP_200_OK,
            )

        intake = Intake.objects.create(
            facility_id=facility_id,
            submitted_by=request.user,
            register_family=register_family,
            source_hash=source_hash,
            batch_period_from=period_from,
            batch_period_to=period_to,
            file_path=f"intakes/{source_hash[:12]}",
        )
        for i, (f, data) in enumerate(zip(files, page_bytes), start=1):
            key = storage.store_page(intake.id, i, data)
            IntakeImage.objects.create(
                intake=intake,
                page_number=i,
                object_key=key,
                image_hash=compute_page_hash(data),
                source_label=request.data.get("source_label", "upload"),
            )

        AuditEvent.objects.create(
            actor=request.user, event_type="intake_created",
            subject_type="intake", subject_id=intake.id, facility_id=facility_id,
            metadata={"register_family": register_family, "pages": len(files)},
        )
        return Response(IntakeSerializer(intake).data, status=status.HTTP_201_CREATED)


class IntakeValidateView(APIView):
    """POST /intakes/{id}/validate — run AI/OCR extraction + validation."""

    permission_classes = [IsDataOfficer]

    def post(self, request, intake_id):
        intake = _get_intake_for_officer(request, intake_id)
        if intake is None:
            return Response(status=404)
        images = [storage.fetch_page(img.object_key) for img in intake.images.all()]
        result = process_intake(intake, images)
        intake.refresh_from_db()
        return Response({"result": result, "intake": IntakeSerializer(intake).data})


class IntakeRowsView(APIView):
    """GET /intakes/{id}/rows — extracted rows for review, with per-field
    confidence and the fields still needing confirmation."""

    permission_classes = [IsAuthenticated]

    def get(self, request, intake_id):
        intake = self._authorized_intake(request, intake_id)
        if intake is None:
            return Response(status=404)
        return Response(SourceRowSerializer(intake.rows.all(), many=True).data)

    @staticmethod
    def _authorized_intake(request, intake_id):
        user = request.user
        qs = Intake.objects.filter(pk=intake_id)
        if user.role == Role.DATA_OFFICER:
            return qs.filter(submitted_by=user).first()
        if user.role == Role.FACILITY_LEAD:
            return qs.filter(facility_id=user.facility_id).first()
        if user.role == Role.SYSTEMS_ADMIN:
            return qs.first()
        return None  # organisation users rejected


class ConfirmFieldView(APIView):
    """POST /intakes/{id}/rows/{rowId}/confirm-field — confirm or correct one
    field. Blocked while a register-family mismatch is unresolved."""

    permission_classes = [IsAuthenticated]

    def post(self, request, intake_id, row_id):
        intake = IntakeRowsView._authorized_intake(request, intake_id)
        if intake is None or request.user.role == Role.ORGANISATION_USER:
            return Response(status=404)
        if intake.register_mismatch_status == RegisterMismatchStatus.FLAGGED:
            return Response({"detail": "Resolve the register-family mismatch first."}, status=409)
        row = SourceRow.objects.filter(pk=row_id, intake=intake).first()
        if row is None:
            return Response(status=404)
        field = request.data.get("field")
        if not field:
            return Response({"detail": "field is required."}, status=400)
        correct = bool(request.data.get("correct", False))
        value = request.data.get("value")
        confirm_field(row, field, value, request.user, correct=correct)
        return Response(SourceRowSerializer(row).data)


class ResolveMismatchView(APIView):
    """POST /intakes/{id}/resolve-register-mismatch — confirm declared family
    or switch to the detected one (re-resolves template, re-runs extraction)."""

    permission_classes = [IsDataOfficer]

    def post(self, request, intake_id):
        intake = _get_intake_for_officer(request, intake_id)
        if intake is None:
            return Response(status=404)
        action = request.data.get("action")
        if action not in ("confirm_declared", "switch"):
            return Response({"detail": "action must be 'confirm_declared' or 'switch'."}, status=400)
        images = [storage.fetch_page(img.object_key) for img in intake.images.all()]
        try:
            out = resolve_register_mismatch(intake, action, request.user, images)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        AuditEvent.objects.create(
            actor=request.user, event_type="register_mismatch_resolved",
            subject_type="intake", subject_id=intake.id, metadata={"action": action},
        )
        intake.refresh_from_db()
        return Response({"result": out, "intake": IntakeSerializer(intake).data})


class PublishView(APIView):
    """POST /intakes/{id}/publish — idempotent publish once every gate passes."""

    permission_classes = [IsDataOfficer]

    def post(self, request, intake_id):
        intake = _get_intake_for_officer(request, intake_id)
        if intake is None:
            return Response(status=404)
        try:
            out = publish_intake(intake, request.user)
        except PublishError as exc:
            return Response({"detail": str(exc)}, status=409)
        AuditEvent.objects.create(
            actor=request.user, event_type="intake_published",
            subject_type="intake", subject_id=intake.id, facility_id=intake.facility_id,
        )
        return Response(out)


class FlagView(APIView):
    """POST /intakes/{id}/flag — data officer flags a template mismatch."""

    permission_classes = [IsDataOfficer]

    def post(self, request, intake_id):
        intake = _get_intake_for_officer(request, intake_id)
        if intake is None:
            return Response(status=404)
        flag = TemplateFlag.objects.create(
            intake=intake, flagged_by=request.user, note=request.data.get("note") or None
        )
        return Response(TemplateFlagSerializer(flag).data, status=201)


class MappingView(APIView):
    """GET /intakes/{id}/mapping — unmatched labels + open flags + canonical
    fields, for the Systems-admin template-mapping screen."""

    permission_classes = [IsSystemsAdmin]

    def get(self, request, intake_id):
        intake = Intake.objects.filter(pk=intake_id).first()
        if intake is None:
            return Response(status=404)
        unmatched = sorted({label for row in intake.rows.all() for label in (row.unmatched_labels or [])})
        canonical = []
        if intake.template:
            canonical = [
                {"canonical_field": c["canonical_field"], "label": c["label"]}
                for c in intake.template.schema.get("columns", [])
            ]
        flags = TemplateFlag.objects.filter(intake=intake, status=TemplateFlag.Status.OPEN)
        return Response({
            "unmatched_labels": unmatched,
            "canonical_fields": canonical,
            "open_flags": TemplateFlagSerializer(flags, many=True).data,
        })


class MyIntakesView(APIView):
    """GET /my-intakes — a data officer's own submission history, every facility."""

    permission_classes = [IsDataOfficer]

    def get(self, request):
        facility_id = request.query_params.get("facility")
        qs = Intake.objects.filter(submitted_by=request.user).select_related("facility")
        if facility_id:
            qs = qs.filter(facility_id=facility_id)
        return Response(IntakeSerializer(qs, many=True).data)


class TemplateListCreateView(APIView):
    """GET/POST /templates — Systems admin lists or creates/clones a template."""

    permission_classes = [IsSystemsAdmin]

    def get(self, request):
        return Response(TemplateSerializer(Template.objects.all(), many=True).data)

    def post(self, request):
        serializer = TemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        AuditEvent.objects.create(
            actor=request.user, event_type="template_created",
            subject_type="template", subject_id=template.id,
            metadata={"register_family": template.register_family, "version": template.version},
        )
        return Response(TemplateSerializer(template).data, status=201)
