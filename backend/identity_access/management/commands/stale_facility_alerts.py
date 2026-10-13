"""Stale-facility alerting (cureva-docs/06).

A facility with no new intake for the configured threshold
(`stale_facility_alert_days`, default 14) triggers a notification to its
Facility lead and to any organisation granted access to it, each on their OWN
configured channel. Both the threshold and the channel are configuration, never
code. Run on a schedule (django-q) or manually:

    python manage.py stale_facility_alerts
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from identity_access.constants import STALE_FACILITY_ALERT
from identity_access.models import Facility, Organisation, Role, User
from identity_access.notifications import notify_user
from identity_access.services import get_setting
from identity_access.settings_registry import STALE_FACILITY_ALERT_DAYS


class Command(BaseCommand):
    help = "Notify recipients of facilities that have gone stale (no recent intake)."

    def handle(self, *args, **options):
        from intelligence.scoping import resolve_org_facility_ids
        from register_intake.models import Intake, IntakeStatus

        threshold_days = int(get_setting(STALE_FACILITY_ALERT_DAYS))
        cutoff = timezone.now() - timedelta(days=threshold_days)

        notified = 0
        for facility in Facility.objects.filter(is_active=True):
            last = (
                Intake.objects.filter(facility=facility, status=IntakeStatus.PUBLISHED)
                .order_by("-published_at")
                .values_list("published_at", flat=True)
                .first()
            )
            is_stale = last is None or last < cutoff
            if not is_stale:
                continue

            subject = f"Cureva Care: {facility.name} has no recent intake"
            days = "no intake on record" if last is None else f"{(timezone.now() - last).days} days since the last intake"
            message = (
                f"{facility.name} has gone past the {threshold_days}-day reporting window "
                f"({days}). Please check whether a register batch is due."
            )

            recipients = list(User.objects.filter(role=Role.FACILITY_LEAD, facility=facility, is_active=True))
            for org in Organisation.objects.filter(is_active=True):
                if facility.id in resolve_org_facility_ids(org.id):
                    recipients.extend(org.users.filter(is_active=True))

            for user in recipients:
                # The stale status stands even if a given channel send fails.
                notify_user(user, STALE_FACILITY_ALERT, subject, message)
                notified += 1

        self.stdout.write(self.style.SUCCESS(f"Stale-facility check complete. Notifications attempted: {notified}."))
