from collections.abc import Iterable

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import (
    ASGIApp,
    Message,
    Receive,
    Scope,
    Send,
)


UNSAFE_METHODS = {
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
}


class ApplicationSecurityMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        allowed_origins: Iterable[str],
        auth_cookie_name: str,
        hsts_enabled: bool,
        hsts_max_age_seconds: int,
        hsts_include_subdomains: bool,
    ) -> None:
        self.app = app
        self.allowed_origins = {
            origin.rstrip("/")
            for origin in allowed_origins
        }
        self.auth_cookie_name = auth_cookie_name
        self.hsts_enabled = hsts_enabled
        self.hsts_max_age_seconds = hsts_max_age_seconds
        self.hsts_include_subdomains = (
            hsts_include_subdomains
        )

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if self._is_cross_site_cookie_request(scope):
            response = JSONResponse(
                status_code=403,
                content={
                    "detail": "Request origin is not allowed.",
                },
            )

            async def send_rejection(
                message: Message,
            ) -> None:
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    self._set_security_headers(
                        headers=headers,
                        path=scope.get("path", ""),
                    )

                await send(message)

            await response(scope, receive, send_rejection)
            return

        async def send_with_security_headers(
            message: Message,
        ) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                self._set_security_headers(
                    headers=headers,
                    path=scope.get("path", ""),
                )

            await send(message)

        await self.app(
            scope,
            receive,
            send_with_security_headers,
        )

    def _is_cross_site_cookie_request(
        self,
        scope: Scope,
    ) -> bool:
        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")

        if (
            method not in UNSAFE_METHODS
            or not path.startswith("/api/")
        ):
            return False

        request_headers = MutableHeaders(
            raw=scope.get("headers", []),
        )
        cookie_header = request_headers.get("cookie", "")

        if not self._contains_auth_cookie(cookie_header):
            return False

        origin = request_headers.get("origin")

        if origin is not None:
            return origin.rstrip("/") not in self.allowed_origins

        fetch_site = request_headers.get("sec-fetch-site")

        if fetch_site is None:
            return False

        return fetch_site.casefold() not in {
            "same-origin",
            "same-site",
            "none",
        }

    def _contains_auth_cookie(
        self,
        cookie_header: str,
    ) -> bool:
        cookie_names = {
            pair.partition("=")[0].strip()
            for pair in cookie_header.split(";")
            if "=" in pair
        }

        return self.auth_cookie_name in cookie_names

    def _set_security_headers(
        self,
        *,
        headers: MutableHeaders,
        path: str,
    ) -> None:
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["Referrer-Policy"] = "no-referrer"
        headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        headers["Cross-Origin-Opener-Policy"] = (
            "same-origin"
        )
        headers["X-Permitted-Cross-Domain-Policies"] = (
            "none"
        )

        if path.startswith("/api/auth/"):
            headers["Cache-Control"] = "no-store"
            headers["Pragma"] = "no-cache"

        if self.hsts_enabled:
            hsts_value = (
                f"max-age={self.hsts_max_age_seconds}"
            )

            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"

            headers["Strict-Transport-Security"] = hsts_value
