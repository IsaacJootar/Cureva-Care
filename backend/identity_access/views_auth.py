"""Authentication endpoints (magic-link + Google SSO), owned by Django.

The Next.js app never talks to an identity provider directly for session
issuance — Django runs the magic-link generation and the OAuth handshake and
hands back a JWT (cureva-docs/05-api-routes.md).
"""
import secrets

from django.conf import settings
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import auth_service
from .serializers import SelfUserSerializer


def _google_redirect_uri(request):
    return request.build_absolute_uri("/api/v1/auth/google/callback")


class MagicLinkRequestView(APIView):
    """POST /auth/magic-link — request a magic link for an email address.

    Always returns 200 with the same body, whether or not the address is
    registered (never reveal account existence). Rate-limited per IP.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "magic_link"
    authentication_classes = []

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response(
                {"detail": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        auth_service.send_magic_link(email)
        return Response(
            {"detail": "If that email is registered, a sign-in link is on its way."}
        )


class SessionExchangeView(APIView):
    """POST /auth/session — exchange a single-use sign-in ticket (from a magic
    link or an SSO callback) for a JWT access+refresh pair."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "session_exchange"
    authentication_classes = []

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        if not token:
            return Response(
                {"detail": "A sign-in token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = auth_service.consume_signin_ticket(token)
        if user is None:
            return Response(
                {"detail": "This sign-in link is invalid, expired, or already used."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        tokens = auth_service.issue_jwt(user)
        return Response(
            {**tokens, "user": SelfUserSerializer(user).data}
        )


class GoogleStartView(APIView):
    """GET /auth/google/start — begin the Google OAuth handshake."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        if not settings.GOOGLE_OAUTH_CLIENT_ID:
            return Response(
                {"detail": "Google SSO is not configured on this deployment."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        state = secrets.token_urlsafe(16)
        request.session["google_oauth_state"] = state
        url = auth_service.google_authorization_url(
            redirect_uri=_google_redirect_uri(request), state=state
        )
        return redirect(url)


class GoogleCallbackView(APIView):
    """GET /auth/google/callback — Google redirects here with a code. We verify
    it, look up the (already-invited) user, mint a sign-in ticket, and bounce
    back to the frontend /login?token=... where the normal exchange happens."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        code = request.GET.get("code")
        state = request.GET.get("state")
        expected_state = request.session.pop("google_oauth_state", None)
        frontend = settings.FRONTEND_ORIGIN

        if not code or not state or state != expected_state:
            return redirect(f"{frontend}/login?error=sso_state")

        email = auth_service.google_exchange_code(
            code=code, redirect_uri=_google_redirect_uri(request)
        )
        if not email:
            return redirect(f"{frontend}/login?error=sso_failed")

        user = auth_service.find_active_user_by_email(email)
        if user is None:
            # Invite-only: SSO never creates an account.
            return redirect(f"{frontend}/login?error=not_invited")

        ticket = auth_service.mint_signin_ticket(user)
        return redirect(f"{frontend}/login?token={ticket}")
