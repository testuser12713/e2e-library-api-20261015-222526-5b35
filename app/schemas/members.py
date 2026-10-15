"""Request and response models for members."""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_EMAIL_ERROR = "value is not a valid email address"


def normalise_email(value: str) -> str:
    """Validate an e-mail address and normalise it to lower case.

    Raises :class:`ValueError` for a malformed address so pydantic reports it as
    a validation error (422) carrying the offending field.
    """
    normalised = value.strip().lower()
    if not _EMAIL_RE.match(normalised):
        raise ValueError(_EMAIL_ERROR)
    return normalised


class MemberCreate(BaseModel):
    name: str
    email: str
    member_since: date

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        return normalise_email(value)


class MemberPatch(BaseModel):
    name: str | None = None
    email: str | None = None
    member_since: date | None = None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalise_email(value)


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    member_since: date


class MemberList(BaseModel):
    items: list[MemberRead]
    total: int
    limit: int
    offset: int
