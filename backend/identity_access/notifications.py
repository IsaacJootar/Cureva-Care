"""Notification delivery — per-user, per-type channel resolution.

A notification job never assumes a channel: it resolves each recipient's
`notification_preferences` row and sends on exactly the channel(s) recorded
there ('none' = silently skipped). SMS goes through Termii (the settled
provider), behind this module's own interface so a future swap stays
one-module. A failed send is logged and never blocks the event it notifies
about (cureva-docs/02, 04).
"""
import logging

import requests
from django.conf import settings
from django.core.mail import send_mail

from .models import NotificationChannel, NotificationPreference

log = logging.getLogger("cureva.notifications")

TERMII_SEND_URL = "https://api.ng.termii.com/api/sms/send"


def send_sms(phone: str, message: str) -> bool:
    """Send one SMS via Termii. Returns success; never raises."""
    if not settings.TERMII_API_KEY:
        log.warning("Termii API key not configured; SMS skipped.")
        return False
    try:
        resp = requests.post(
            TERMII_SEND_URL,
            json={
                "to": phone,
                "from": settings.TERMII_SENDER_ID,
                "sms": message,
                "type": "plain",
                "channel": "generic",
                "api_key": settings.TERMII_API_KEY,
            },
            timeout=10,
        )
        if resp.status_code // 100 == 2:
            return True
        log.error("Termii send failed: %s", resp.status_code)
        return False
    except requests.RequestException as exc:
        log.error("Termii send error: %s", exc)
        return False


def send_email_notification(email: str, subject: str, message: str) -> bool:
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        return True
    except Exception as exc:  # noqa: BLE001 — never block on a failed send
        log.error("Email send error: %s", exc)
        return False


def notify_user(user, notification_type: str, subject: str, message: str) -> dict:
    """Resolve the user's channel for this notification type and send. Each
    channel is attempted independently; failures are logged, not raised."""
    pref = NotificationPreference.objects.filter(user=user, notification_type=notification_type).first()
    channel = pref.channel if pref else NotificationChannel.EMAIL_AND_SMS

    results = {"email": None, "sms": None}
    if channel in (NotificationChannel.EMAIL, NotificationChannel.EMAIL_AND_SMS):
        results["email"] = send_email_notification(user.email, subject, message)
    if channel in (NotificationChannel.SMS, NotificationChannel.EMAIL_AND_SMS):
        if user.phone:
            results["sms"] = send_sms(user.phone, message)
        else:
            log.info("User %s has no phone; SMS channel skipped.", user.id)
    # channel == NONE -> silently skipped (never defaulted back to email).
    return {"channel": channel, "results": results}
