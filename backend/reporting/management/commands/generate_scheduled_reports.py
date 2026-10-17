"""Scheduled report generation (WS7).

Generates and saves a buyer-specific report per scope, so a monthly/quarterly
brief is waiting without anyone pressing a button. Run on a schedule via django-q
(the same cluster that runs the stale-facility alert) or cron:

    python manage.py generate_scheduled_reports --type facility_operational
    python manage.py generate_scheduled_reports --type ngo_grant

- facility_operational → one report per active facility.
- ngo_grant / government_surveillance → one report per organisation, over the
  facilities that organisation's grants cover.

Reports are saved as SavedReport rows (access-scoped on read like any other), so
scheduling is just "call this command"; no new delivery path is needed.
"""
from django.core.management.base import BaseCommand

from reporting.generator import REPORT_TYPES, build_report, generate_narrative
from reporting.models import SavedReport


class Command(BaseCommand):
    help = "Generate and save scheduled reports for every scope."

    def add_arguments(self, parser):
        parser.add_argument("--type", default="facility_operational", choices=list(REPORT_TYPES))
        parser.add_argument("--with-narrative", action="store_true")

    def handle(self, *args, **opts):
        from identity_access.models import Facility, Organisation

        report_type = opts["type"]
        with_narrative = opts["with_narrative"]
        made = 0

        if report_type == "facility_operational":
            for f in Facility.objects.all():
                self._make(report_type, [str(f.id)], f"{f.name} — operational brief", with_narrative)
                made += 1
        else:
            for org in Organisation.objects.all():
                facility_ids = _org_facilities(org)
                if not facility_ids:
                    continue
                self._make(report_type, facility_ids, f"{org.name} — {REPORT_TYPES[report_type]}", with_narrative)
                made += 1

        self.stdout.write(self.style.SUCCESS(f"Generated {made} {report_type} report(s)."))

    def _make(self, report_type, facility_ids, title, with_narrative):
        sections = build_report(report_type, facility_ids)
        narrative = generate_narrative(sections) if with_narrative else None
        SavedReport.objects.create(
            title=title, report_type=report_type,
            facility_ids=[str(f) for f in facility_ids],
            sections=sections, narrative=narrative, generated_by=None,
        )


def _org_facilities(org) -> list[str]:
    """Facilities an organisation's grants cover (reuses the access scoping)."""
    try:
        from intelligence.scoping import organisation_facility_ids
        return [str(x) for x in organisation_facility_ids(org)]
    except Exception:
        # Fallback: direct facility grants if the helper isn't available.
        return [str(g.scope_id) for g in org.facility_access.all() if getattr(g, "scope_type", "") == "facility"]
