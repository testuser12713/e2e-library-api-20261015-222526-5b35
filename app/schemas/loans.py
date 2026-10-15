"""Request and response models for loans."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.schemas.common import BookRef, MemberRef


class LoanCreate(BaseModel):
    book_id: int
    member_id: int


class LoanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    member_id: int
    loaned_on: date
    due_on: date
    returned_on: date | None


class LoanList(BaseModel):
    items: list[LoanRead]
    total: int
    limit: int
    offset: int


class OverdueLoan(LoanRead):
    book: BookRef
    member: MemberRef
    days_overdue: int


class OverdueLoanList(BaseModel):
    items: list[OverdueLoan]
    total: int
