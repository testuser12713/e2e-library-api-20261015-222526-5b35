"""Application configuration.

Values are read from the environment LAZILY (on every access) so importing this
module never crashes a freshly cloned checkout. Required values are validated
ONCE at startup by :func:`validate_settings`, which names the missing variable.
"""

from __future__ import annotations

import os

DEFAULT_DATABASE_URL = "sqlite:///./library.db"
DEFAULT_LOAN_PERIOD_DAYS = 14
DEFAULT_MAX_OPEN_LOANS = 3


class Settings:
    """Environment-backed settings, read lazily on each attribute access."""

    @property
    def library_api_key(self) -> str | None:
        return os.environ.get("LIBRARY_API_KEY")

    @property
    def library_database_url(self) -> str:
        return os.environ.get("LIBRARY_DATABASE_URL", DEFAULT_DATABASE_URL)

    @property
    def loan_period_days(self) -> int:
        return int(os.environ.get("LOAN_PERIOD_DAYS", str(DEFAULT_LOAN_PERIOD_DAYS)))

    @property
    def max_open_loans(self) -> int:
        return int(os.environ.get("MAX_OPEN_LOANS", str(DEFAULT_MAX_OPEN_LOANS)))


settings = Settings()


def validate_settings() -> None:
    """Validate the whole settings object at startup.

    Raises :class:`RuntimeError` naming the offending variable when a required
    value is absent, so the operator is told what to set instead of getting a
    bare traceback at the first request.
    """
    if not settings.library_api_key:
        raise RuntimeError(
            "LIBRARY_API_KEY is not set. Declare it in RUN.json (for example as a "
            "generated value) or export it before starting the api service."
        )
    if not settings.library_database_url:
        raise RuntimeError(
            "LIBRARY_DATABASE_URL is empty. Set it or rely on the default "
            f"{DEFAULT_DATABASE_URL!r}."
        )
    if settings.loan_period_days <= 0:
        raise RuntimeError("LOAN_PERIOD_DAYS must be a positive integer.")
    if settings.max_open_loans <= 0:
        raise RuntimeError("MAX_OPEN_LOANS must be a positive integer.")
