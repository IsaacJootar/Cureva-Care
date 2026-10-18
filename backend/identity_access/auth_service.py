"""Authentication service — Django owns sign-in.

Sign-in is by email + password, verified here against the admin-set password.
A magic-link path also exists: it mints a single-use, short-lived *sign-in
ticket* (stored hashed in MagicLinkToken) that the frontend exchanges at
POST /auth/session for a JWT access+refresh pair.

Credentials only ever establish WHO someone is; role and facility scope come
exclusively from the admin-managed user record, looked up at login
(cureva-docs/07-security-privacy-access.md). Account creation is invite-only:
a login attempt for an unknown or inactive email never creates a user.
"""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AuditEvent, MagicLinkToken, User


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
    missing or expired. Single-use is enforced here in production; local dev may
    disable it (settings.MAGIC_LINK_SINGLE_USE=False) to reuse a link while
    testing — never do that in production."""
    single_use = getattr(settings, "MAGIC_LINK_SINGLE_USE", True)

    qs = MagicLinkToken.objects.select_related("user").filter(token_hash=_hash(raw_token))
    if single_use:
        qs = qs.filter(used_at__isnull=True)
    row = qs.order_by("-created_at").first()

    # In reusable mode a used row is fine; only expiry matters.
    if row is None or row.expires_at <= timezone.now():
        return None
    if single_use and row.used_at is not None:
        return None

    if single_use:
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


# --- Password sign-in -----------------------------------------------------
def authenticate_password(email: str, password: str) -> User | None:
    """Verify email + password. Invite-only: the user must already exist, be
    active, and have a usable (admin-set) password."""
    user = User.objects.filter(email=email.lower(), is_active=True).first()
    if user is None or not user.has_usable_password():
        return None
    if not user.check_password(password):
        return None
    return user


def find_active_user_by_email(email: str) -> User | None:
    """Invite-only: the user must already exist and be active."""
    return User.objects.filter(email=email.lower(), is_active=True).first()
