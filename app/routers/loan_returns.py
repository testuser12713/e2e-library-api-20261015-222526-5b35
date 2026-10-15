"""Loan return route."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.loans import LoanRead
from app.security import require_api_key
from app.services.loan_returns import return_loan as return_loan_service

router = APIRouter(tags=["loans"])


@router.post(
    "/loans/{loan_id}/return",
    response_model=LoanRead,
    dependencies=[Depends(require_api_key)],
)
def return_loan(loan_id: int, db: Session = Depends(get_db)) -> LoanRead:
    """Return an open loan: set today's return date and free one copy."""
    return return_loan_service(db, loan_id)
