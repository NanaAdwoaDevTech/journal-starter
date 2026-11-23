"""Security headers added to every response."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

HSTS_VALUE = "max-age=31536000; includeSubDomains"


def add_security_headers(app: FastAPI) -> None:
    """Send Strict-Transport-Security on every response."""

    @app.middleware("http")
    async def set_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = HSTS_VALUE
        return response
