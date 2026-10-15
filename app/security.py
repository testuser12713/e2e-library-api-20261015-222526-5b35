"""API-key guard.

Every write endpoint depends on :func:`require_api_key`, which compares the
``X-API-Key`` request header with the configured ``LIBRARY_API_KEY`` and rejects
anything else with a ``401`` in the unified error body. Read endpoints do not use
this dependency.
"""

from __future__ import annotations

import secrets

from fastapi import Header

from app.config import settings
from app.errors import AppError


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Reject a request whose ``X-API-Key`` header is missing or wrong.

    The configured key is read lazily from the settings on every request, so
    importing this module never crashes when ``LIBRARY_API_KEY`` is unset. When
    no key is configured, every request is rejected instead.
    """
    configured = settings.library_api_key
    if (
        not configured
        or not x_api_key
        or not secrets.compare_digest(configured.encode("utf-8"), x_api_key.encode("utf-8"))
    ):
        raise AppError(
            status_code=401,
            code="unauthorized",
            message="A valid X-API-Key header is required.",
        )
