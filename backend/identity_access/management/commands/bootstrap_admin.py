"""Create the first Systems admin so the invite-only chain has a root.

Account creation is invite-only end to end (cureva-docs/07-security): only a
Systems admin can create users. This command seats that first admin from the
CLI (the one account that can't be invited by another). Idempotent on email.

    python manage.py bootstrap_admin --email you@example.com --name "Your Name"
"""
from django.core.management.base import BaseCommand

from identity_access.models import Role, User


class Command(BaseCommand):
    help = "Create (or confirm) the initial Systems admin account."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", required=True)

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        name = options["name"].strip()

        existing = User.objects.filter(email=email).first()
        if existing:
            self.stdout.write(
                self.style.WARNING(
                    f"User {email} already exists (role={existing.role}). No change."
                )
            )
            return

        user = User.objects.create_user(
            email=email, name=name, role=Role.SYSTEMS_ADMIN
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created Systems admin {user.name} <{user.email}>. "
                f"Sign in via magic link at the frontend /login screen."
            )
        )
