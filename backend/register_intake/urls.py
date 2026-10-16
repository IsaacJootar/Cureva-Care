"""Register Intake API routes (mounted under /api/v1/)."""
from django.urls import path

from .views import (
    ConfirmFieldView,
    FlagView,
    IntakeCreateView,
    IntakeDeleteView,
    IntakePagesView,
    IntakeRowsView,
    IntakeValidateView,
    MappingView,
    MyIntakesView,
    ProgressView,
    PublishView,
    ResolveMismatchView,
    TemplateAliasView,
    TemplateFlagsListView,
    TemplateListCreateView,
)

urlpatterns = [
    path("intakes", IntakeCreateView.as_view(), name="intake-create"),
    path("intakes/<uuid:intake_id>", IntakeDeleteView.as_view(), name="intake-delete"),
    path("intakes/<uuid:intake_id>/validate", IntakeValidateView.as_view(), name="intake-validate"),
    path("intakes/<uuid:intake_id>/progress", ProgressView.as_view(), name="intake-progress"),
    path("intakes/<uuid:intake_id>/rows", IntakeRowsView.as_view(), name="intake-rows"),
    path("intakes/<uuid:intake_id>/pages", IntakePagesView.as_view(), name="intake-pages"),
    path("intakes/<uuid:intake_id>/rows/<uuid:row_id>/confirm-field", ConfirmFieldView.as_view(), name="intake-confirm-field"),
    path("intakes/<uuid:intake_id>/publish", PublishView.as_view(), name="intake-publish"),
    path("intakes/<uuid:intake_id>/resolve-register-mismatch", ResolveMismatchView.as_view(), name="intake-resolve-mismatch"),
    path("intakes/<uuid:intake_id>/flag", FlagView.as_view(), name="intake-flag"),
    path("intakes/<uuid:intake_id>/mapping", MappingView.as_view(), name="intake-mapping"),
    path("my-intakes", MyIntakesView.as_view(), name="my-intakes"),
    path("templates", TemplateListCreateView.as_view(), name="templates"),
    path("templates/<uuid:template_id>/aliases", TemplateAliasView.as_view(), name="template-aliases"),
    path("template-flags", TemplateFlagsListView.as_view(), name="template-flags"),
]
