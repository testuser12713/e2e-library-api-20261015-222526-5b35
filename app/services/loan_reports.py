"""Query services for loan listings and the overdue report."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Loan
from app.schemas.common import BookRef, MemberRef
from app.schemas.loans import OverdueLoan


def list_loans(
    db: Session,
    member_id: int | None = None,
    book_id: int | None = None,
    open_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Loan], int]:
    """Return one page of loans plus the size of the filtered set.

    ``total`` counts every matching loan before ``limit``/``offset`` are applied.
    ``open_only`` restricts the result to loans whose ``returned_on`` is unset.
    The page is ordered stably by ``Loan.id``.
    """
    conditions = []
    if member_id is not None:
        conditions.append(Loan.member_id == member_id)
    if book_id is not None:
        conditions.append(Loan.book_id == book_id)
    if open_only:
        conditions.append(Loan.returned_on.is_(None))

    total = db.scalar(select(func.count()).select_from(Loan).where(*conditions)) or 0
    items = list(
        db.scalars(
            select(Loan).where(*conditions).order_by(Loan.id).limit(limit).offset(offset)
        ).all()
    )
    return items, total


def list_overdue(db: Session, today: date) -> tuple[list[OverdueLoan], int]:
    """Return every open loan due before ``today``, with book/member and delay.

    Each entry carries the referenced book and member and ``days_overdue`` =
    ``today`` minus ``due_on``. The list is ordered stably by ``Loan.id``.
    """
    conditions = (Loan.returned_on.is_(None), Loan.due_on < today)

    total = db.scalar(select(func.count()).select_from(Loan).where(*conditions)) or 0
    loans = list(
        db.scalars(
            select(Loan)
            .where(*conditions)
            .options(joinedload(Loan.book), joinedload(Loan.member))
            .order_by(Loan.id)
        ).all()
    )

    items = [
        OverdueLoan(
            id=loan.id,
            book_id=loan.book_id,
            member_id=loan.member_id,
            loaned_on=loan.loaned_on,
            due_on=loan.due_on,
            returned_on=loan.returned_on,
            book=BookRef(
                id=loan.book.id,
                title=loan.book.title,
                author=loan.book.author,
                isbn=loan.book.isbn,
            ),
            member=MemberRef(
                id=loan.member.id,
                name=loan.member.name,
                email=loan.member.email,
            ),
            days_overdue=(today - loan.due_on).days,
        )
        for loan in loans
    ]
    return items, total
