from django.apps import AppConfig


class IdentityAccessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "identity_access"
    verbose_name = "Identity & Access"

    def ready(self):
        # Register signal handlers (default notification preferences per user).
        from . import signals  # noqa: F401
