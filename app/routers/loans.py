"""Loan creation route."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Loan
from app.schemas.loans import LoanCreate, LoanRead
from app.security import require_api_key
from app.services import loans as loan_service

router = APIRouter(tags=["loans"])


@router.post(
    "/loans",
    response_model=LoanRead,
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
def create_loan(payload: LoanCreate, db: Session = Depends(get_db)) -> Loan:
    return loan_service.create_loan(db, payload)
