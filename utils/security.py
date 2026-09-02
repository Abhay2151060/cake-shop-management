"""
CSRF protection.

The app authenticates via a cookie-backed session, so every state-changing
request (HTML form POST and JSON fetch POST alike) is forgeable from a third
party site unless a token bound to the session is required.

Design goals:
  * Least disruptive: tokens are injected into templates automatically and into
    fetch() calls via a single global helper, so no route signatures change.
  * Safe by default: unsafe methods are rejected unless a valid token is present.
"""

import hmac
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, PlainTextResponse

CSRF_SESSION_KEY = "csrf_token"
CSRF_FORM_FIELD = "csrf_token"
CSRF_HEADER = "x-csrf-token"

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def get_csrf_token(request) -> str:
    """Return the session's CSRF token, creating one on first use."""
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


class CSRFMiddleware:
    """Rejects unsafe requests that do not carry the session's CSRF token."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        if method in SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        session = scope.get("session") or {}
        session_token = session.get(CSRF_SESSION_KEY)

        submitted = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"x-csrf-token":
                submitted = value.decode("latin1", errors="replace")
                break

        app_receive = receive
        if not submitted:
            content_type = ""
            for name, value in scope.get("headers", []):
                if name.lower() == b"content-type":
                    content_type = value.decode("latin1", errors="replace")
                    break

            if content_type.startswith(("application/x-www-form-urlencoded", "multipart/form-data")):
                body_chunks = []
                more_body = True
                while more_body:
                    message = await receive()
                    if message["type"] == "http.request":
                        body_chunks.append(message.get("body", b""))
                        more_body = message.get("more_body", False)
                    else:
                        break
                body_bytes = b"".join(body_chunks)

                sent1 = False
                async def receive_for_form():
                    nonlocal sent1
                    if not sent1:
                        sent1 = True
                        return {"type": "http.request", "body": body_bytes, "more_body": False}
                    return {"type": "http.request", "body": b"", "more_body": False}

                from starlette.requests import Request
                req = Request(scope, receive_for_form)
                try:
                    form = await req.form()
                    submitted = form.get(CSRF_FORM_FIELD)
                except Exception:
                    submitted = None

                sent2 = False
                async def receive_for_app():
                    nonlocal sent2
                    if not sent2:
                        sent2 = True
                        return {"type": "http.request", "body": body_bytes, "more_body": False}
                    return {"type": "http.request", "body": b"", "more_body": False}

                app_receive = receive_for_app

        if not session_token or not submitted or not hmac.compare_digest(str(session_token), str(submitted)):
            accepts_json = False
            for name, value in scope.get("headers", []):
                val_str = value.decode("latin1", errors="replace")
                if name.lower() == b"accept" and "application/json" in val_str:
                    accepts_json = True
                    break
                if name.lower() == b"content-type" and val_str.startswith("application/json"):
                    accepts_json = True
                    break

            message = "CSRF token missing or invalid. Please reload the page and try again."
            if accepts_json:
                res = JSONResponse({"success": False, "error": message}, status_code=403)
            else:
                res = PlainTextResponse(message, status_code=403)
            await res(scope, receive, send)
            return

        await self.app(scope, app_receive, send)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds baseline browser hardening headers to every response."""

    def __init__(self, app, https_only: bool = False):
        super().__init__(app)
        self.https_only = https_only

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()"
        )
        # Templates rely on inline styles/handlers, so 'unsafe-inline' is required
        # for this codebase; the directives still block third-party script origins
        # other than the two CDNs actually used, and forbid framing entirely.
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        if self.https_only:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains"
            )
        return response
