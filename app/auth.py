"""Google sign-in gate (design §5 / DoS #4) — id_token verification + email allowlist.

The client signs in with Google Identity Services and sends the resulting id_token as a Bearer on
/api/* calls. This module verifies the token against Google's keys (signature + aud + iss + exp via
google-auth) and checks the email against the allowlist. Unauthenticated callers get 401/403 so the
SPA shows a sign-in screen, never the portfolio (DoS #4: no unauthenticated access; PROD promote stays
human). DEV mode (AUTH_ENABLED=false) bypasses with a dev user so Phase-A build/test needs no live token;
PROD MUST run AUTH_ENABLED=true with a populated ALLOWED_EMAILS.
"""
from __future__ import annotations

from fastapi import HTTPException, Request

from app.config import settings

_GOOGLE_ISS = {"accounts.google.com", "https://accounts.google.com"}


def verify_google_id_token(token: str) -> dict:
    """Verify a Google id_token and return its claims. Raises on any failure (bad sig/aud/iss/exp)."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    info = google_id_token.verify_oauth2_token(
        token, google_requests.Request(), settings.google_client_id
    )
    if info.get("iss") not in _GOOGLE_ISS:
        raise ValueError("bad issuer")
    return info


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth[:7].lower() == "bearer ":
        return auth[7:].strip()
    return request.cookies.get("fops_idtoken")


async def require_user(request: Request) -> dict:
    """Auth dependency for the SPA + /api/*.

    DEV (AUTH_ENABLED=false): bypass with a dev user (no live Google token needed for Phase-A build).
    PROD (AUTH_ENABLED=true): verify the Google id_token + require the email be verified AND on the
    allowlist. 401 (no/invalid token) or 403 (not allowlisted) -> the SPA renders the sign-in screen.
    """
    if not settings.auth_enabled:
        return {"email": "dev@localhost", "dev": True}
    token = _bearer(request)
    if not token:
        raise HTTPException(401, "sign-in required")
    try:
        info = verify_google_id_token(token)
    except Exception as exc:  # noqa: BLE001 — any verification failure is a 401, details never leaked
        raise HTTPException(401, "invalid or expired sign-in") from exc
    if not info.get("email_verified", False):
        raise HTTPException(403, "email not verified")
    email = (info.get("email") or "").lower()
    allow = settings.allowed_email_set
    if allow and email not in allow:
        raise HTTPException(403, "not authorized for this console")
    return {"email": email}
