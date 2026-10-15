"""Request and response models for members.

Declarative types only — the e-mail validator belongs to the member feature
ticket.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class MemberCreate(BaseModel):
    name: str
    email: str
    member_since: date


class MemberPatch(BaseModel):
    name: str | None = None
    email: str | None = None
    member_since: date | None = None


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
