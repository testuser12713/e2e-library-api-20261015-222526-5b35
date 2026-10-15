"""Loan creation rules: copy availability and the per-member open-loan limit."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError
from app.models import Book, Loan, Member
from app.schemas.loans import LoanCreate


def create_loan(db: Session, payload: LoanCreate) -> Loan:
    """Create a loan for ``payload`` or raise the matching application error.

    An unknown book or member answers ``404``. A book with no free copy and a
    member that already holds ``MAX_OPEN_LOANS`` open loans answer ``409`` with a
    message naming the reason. On success the book's ``copies_available`` is
    decremented and the new loan is persisted with ``loaned_on`` = today (UTC),
    ``due_on`` = today + ``LOAN_PERIOD_DAYS`` and ``returned_on`` = ``None``.
    """
    book = db.get(Book, payload.book_id)
    if book is None:
        raise AppError(404, "not_found", f"Book {payload.book_id} was not found.")

    member = db.get(Member, payload.member_id)
    if member is None:
        raise AppError(404, "not_found", f"Member {payload.member_id} was not found.")

    if book.copies_available <= 0:
        raise AppError(
            409,
            "conflict",
            f"Book {book.id} has no free copy available.",
        )

    open_loans = db.scalar(
        select(func.count())
        .select_from(Loan)
        .where(Loan.member_id == member.id, Loan.returned_on.is_(None))
    )
    if open_loans is not None and open_loans >= settings.max_open_loans:
        raise AppError(
            409,
            "conflict",
            f"Member {member.id} has reached the open-loan limit of "
            f"{settings.max_open_loans} loans.",
        )

    loaned_on = datetime.now(UTC).date()
    loan = Loan(
        book_id=book.id,
        member_id=member.id,
        loaned_on=loaned_on,
        due_on=loaned_on + timedelta(days=settings.loan_period_days),
        returned_on=None,
    )
    book.copies_available -= 1
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan
