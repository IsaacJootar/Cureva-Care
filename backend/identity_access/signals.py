"""Signal handlers for Identity & Access."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .constants import NOTIFICATION_TYPES
from .models import NotificationChannel, NotificationPreference, User


@receiver(post_save, sender=User)
def create_default_notification_preferences(sender, instance, created, **kwargs):
    """Every new user gets a default channel preference per notification type
    (email_and_sms), which they can later change themselves. The job that
    sends a notification reads this row rather than assuming a channel
    (cureva-docs/02-data-model.md)."""
    if not created:
        return
    NotificationPreference.objects.bulk_create(
        [
            NotificationPreference(
                user=instance,
                notification_type=nt,
                channel=NotificationChannel.EMAIL_AND_SMS,
            )
            for nt in NOTIFICATION_TYPES
        ],
        ignore_conflicts=True,
    )
