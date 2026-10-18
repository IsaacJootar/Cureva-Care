"""Authentication endpoints (email+password and magic-link), owned by Django.

The Next.js app authenticates against Django, which verifies credentials and
hands back a JWT access+refresh pair (cureva-docs/05-api-routes.md). Accounts are
invite-only: an admin creates the user and sets an initial password; the user can
change it themselves. Magic-link sign-in is also available.
"""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import auth_service
from .serializers import SelfUserSerializer


class PasswordLoginView(APIView):
    """POST /auth/login — email + password → JWT. Rate-limited per IP."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "magic_link"
    authentication_classes = []

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        if not email or not password:
            return Response({"detail": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)
        user = auth_service.authenticate_password(email, password)
        if user is None:
            return Response({"detail": "Incorrect email or password."}, status=status.HTTP_401_UNAUTHORIZED)
        tokens = auth_service.issue_jwt(user)
        return Response({**tokens, "user": SelfUserSerializer(user).data})


class ChangePasswordView(APIView):
    """POST /auth/change-password — a signed-in user sets a new password."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        current = request.data.get("current_password") or ""
        new = request.data.get("new_password") or ""
        if len(new) < 8:
            return Response({"detail": "New password must be at least 8 characters."}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.check_password(current):
            return Response({"detail": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(new)
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password changed."})


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
