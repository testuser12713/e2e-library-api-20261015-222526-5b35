"""Loan listing and overdue report routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.loans import LoanList, OverdueLoanList
from app.services.loan_reports import list_loans as list_loans_service
from app.services.loan_reports import list_overdue as list_overdue_service

router = APIRouter(tags=["loans"])


@router.get("/loans", response_model=LoanList)
def list_loans(
    member_id: int | None = None,
    book_id: int | None = None,
    open_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> LoanList:
    """List loans with optional filters, paginated and stably sorted by id."""
    items, total = list_loans_service(
        db,
        member_id=member_id,
        book_id=book_id,
        open_only=open_only,
        limit=limit,
        offset=offset,
    )
    return LoanList(items=items, total=total, limit=limit, offset=offset)


@router.get("/loans/overdue", response_model=OverdueLoanList)
def list_overdue_loans(db: Session = Depends(get_db)) -> OverdueLoanList:
    """Report every open loan whose due date lies before today."""
    today = datetime.now(UTC).date()
    items, total = list_overdue_service(db, today)
    return OverdueLoanList(items=items, total=total)
