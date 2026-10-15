"""API-key guard.

The final signature of :func:`require_api_key` lives here. The actual guard is
implemented by the ticket that enforces the ``X-API-Key`` header on every write
endpoint; until then the body is intentionally empty.
"""

from __future__ import annotations

from fastapi import Header


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Validate the ``X-API-Key`` header. Implementation follows in its own ticket."""
