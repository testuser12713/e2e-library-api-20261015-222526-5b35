"""Loan creation and listing routes — stubs until their tickets fill them."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.errors import AppError
from app.schemas.loans import LoanCreate, LoanList, LoanRead
from app.security import require_api_key

router = APIRouter(tags=["loans"])


def _not_implemented() -> AppError:
    return AppError(
        status_code=501,
        code="not_implemented",
        message="Loan routes are implemented by their feature tickets.",
    )


@router.post(
    "/loans",
    response_model=LoanRead,
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
def create_loan(payload: LoanCreate) -> LoanRead:
    raise _not_implemented()


@router.get("/loans", response_model=LoanList)
def list_loans(
    member_id: int | None = None,
    book_id: int | None = None,
    open_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> LoanList:
    raise _not_implemented()
