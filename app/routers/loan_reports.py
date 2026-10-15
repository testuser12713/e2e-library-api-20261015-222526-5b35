"""Loan overdue report route — stub until its ticket fills it."""

from __future__ import annotations

from fastapi import APIRouter

from app.errors import AppError
from app.schemas.loans import OverdueLoanList

router = APIRouter(tags=["loans"])


@router.get("/loans/overdue", response_model=OverdueLoanList)
def list_overdue_loans() -> OverdueLoanList:
    raise AppError(
        status_code=501,
        code="not_implemented",
        message="The overdue report is implemented by its feature ticket.",
    )
