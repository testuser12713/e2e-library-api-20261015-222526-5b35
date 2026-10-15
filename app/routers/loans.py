"""Loan creation and listing routes — stubs until their tickets fill them."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AppError
from app.models import Loan
from app.schemas.loans import LoanCreate, LoanList, LoanRead
from app.security import require_api_key
from app.services import loans as loan_service

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
def create_loan(payload: LoanCreate, db: Session = Depends(get_db)) -> Loan:
    return loan_service.create_loan(db, payload)


@router.get("/loans", response_model=LoanList)
def list_loans(
    member_id: int | None = None,
    book_id: int | None = None,
    open_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> LoanList:
    raise _not_implemented()
