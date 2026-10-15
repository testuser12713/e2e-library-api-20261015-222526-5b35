"""Loan return route — stub until the loan return ticket fills it."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.errors import AppError
from app.schemas.loans import LoanRead
from app.security import require_api_key

router = APIRouter(tags=["loans"])


@router.post(
    "/loans/{loan_id}/return",
    response_model=LoanRead,
    dependencies=[Depends(require_api_key)],
)
def return_loan(loan_id: int) -> LoanRead:
    raise AppError(
        status_code=501,
        code="not_implemented",
        message="Loan return is implemented by its feature ticket.",
    )
