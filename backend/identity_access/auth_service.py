"""Authentication service — Django owns both sign-in paths.

Both magic-link and Google SSO converge on a single-use, short-lived *sign-in
ticket* (stored hashed in MagicLinkToken). The frontend exchanges that ticket
at POST /auth/session for a JWT access+refresh pair. This keeps the long-lived
credential out of any URL, and gives both paths one identical final step.

Magic-link or SSO only ever establishes WHO someone is; role and facility
scope come exclusively from the admin-managed user record, looked up at login
(cureva-docs/07-security-privacy-access.md). Account creation is invite-only:
a login attempt for an unknown or inactive email never creates a user.
"""
import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AuditEvent, MagicLinkToken, User

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def mint_signin_ticket(user: User) -> str:
    """Create a single-use, short-lived ticket for this user and return the
    RAW token (stored only as a hash). Used by both magic-link and SSO."""
    raw = secrets.token_urlsafe(32)
    MagicLinkToken.objects.create(
        user=user,
        token_hash=_hash(raw),
        expires_at=timezone.now() + timedelta(minutes=settings.MAGIC_LINK_TTL_MINUTES),
    )
    return raw


def consume_signin_ticket(raw_token: str) -> User | None:
    """Consume a ticket. Returns the user on success, None if the ticket is
    missing, expired, or already used. Single-use is enforced here."""
    row = (
        MagicLinkToken.objects.select_related("user")
        .filter(token_hash=_hash(raw_token), used_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if row is None or not row.is_consumable:
        return None
    row.used_at = timezone.now()
    row.save(update_fields=["used_at"])
    if not row.user.is_active:
        return None
    return row.user


def issue_jwt(user: User) -> dict:
    """Issue an access+refresh JWT pair and audit the login."""
    refresh = RefreshToken.for_user(user)
    AuditEvent.objects.create(
        actor=user,
        event_type="login",
        metadata={"role": user.role},  # non-PHI
    )
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


# --- Magic-link -----------------------------------------------------------
def send_magic_link(email: str) -> None:
    """Send a magic-link email IF the address belongs to an active user.
    Silent no-op otherwise (never reveal whether an address is registered)."""
    user = User.objects.filter(email=email.lower(), is_active=True).first()
    if user is None:
        return
    raw = mint_signin_ticket(user)
    link = f"{settings.FRONTEND_ORIGIN}/login?token={raw}"
    send_mail(
        subject="Your Cureva Care sign-in link",
        message=(
            f"Hello {user.name},\n\n"
            f"Use this link to sign in to Cureva Care. It expires in "
            f"{settings.MAGIC_LINK_TTL_MINUTES} minutes and can be used once:\n\n"
            f"{link}\n\n"
            f"If you didn't request this, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


# --- Google SSO -----------------------------------------------------------
def google_authorization_url(redirect_uri: str, state: str) -> str:
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def google_exchange_code(code: str, redirect_uri: str) -> str | None:
    """Exchange an authorization code for the signed-in user's email address.
    Returns the email, or None on failure."""
    token_resp = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if token_resp.status_code != 200:
        return None
    access_token = token_resp.json().get("access_token")
    if not access_token:
        return None
    userinfo_resp = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if userinfo_resp.status_code != 200:
        return None
    info = userinfo_resp.json()
    if not info.get("email_verified", False):
        return None
    return (info.get("email") or "").lower() or None


def find_active_user_by_email(email: str) -> User | None:
    """Invite-only: the user must already exist and be active."""
    return User.objects.filter(email=email.lower(), is_active=True).first()
