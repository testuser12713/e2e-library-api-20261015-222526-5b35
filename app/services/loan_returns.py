"""Business logic for returning a loan."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Book, Loan


def return_loan(db: Session, loan_id: int) -> Loan:
    """Mark an open loan as returned today and free one book copy.

    Raises :class:`AppError` with ``not_found`` when the loan does not exist and
    with ``conflict`` when it has already been returned, leaving the existing
    return date untouched in that case.
    """
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise AppError(
            status_code=404,
            code="not_found",
            message=f"Loan {loan_id} not found",
        )
    if loan.returned_on is not None:
        raise AppError(
            status_code=409,
            code="conflict",
            message=f"Loan {loan_id} has already been returned",
        )

    book = db.get(Book, loan.book_id)
    if book is None:
        raise AppError(
            status_code=404,
            code="not_found",
            message=f"Book {loan.book_id} not found",
        )

    loan.returned_on = datetime.now(UTC).date()
    book.copies_available += 1

    db.commit()
    db.refresh(loan)
    return loan
