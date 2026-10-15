"""Tests for loan listing and the overdue report.

Every assertion is scoped to the rows this module seeds, because the shared test
database is created once per run and other test modules keep their own rows.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, Loan, Member
from app.routers import loan_reports
from app.services.loan_reports import list_loans, list_overdue


def _book(db: Session, isbn: str, title: str = "Title") -> Book:
    book = Book(
        title=title,
        author="Author",
        isbn=isbn,
        publication_year=2000,
        copies_total=3,
        copies_available=1,
    )
    db.add(book)
    db.flush()
    return book


def _member(db: Session, email: str, name: str = "Member") -> Member:
    member = Member(name=name, email=email, member_since=date(2020, 1, 1))
    db.add(member)
    db.flush()
    return member


def _loan(
    db: Session,
    book: Book,
    member: Member,
    loaned_on: date,
    due_on: date,
    returned_on: date | None = None,
) -> Loan:
    loan = Loan(
        book_id=book.id,
        member_id=member.id,
        loaned_on=loaned_on,
        due_on=due_on,
        returned_on=returned_on,
    )
    db.add(loan)
    db.flush()
    return loan


def test_list_loans_returns_all_ordered_by_id(db_session: Session) -> None:
    book = _book(db_session, "isbn-all")
    member = _member(db_session, "all@example.com")
    today = date(2024, 5, 1)
    first = _loan(db_session, book, member, today, today + timedelta(days=14))
    second = _loan(db_session, book, member, today, today + timedelta(days=14))
    db_session.commit()

    items, total = list_loans(db_session, book_id=book.id, limit=50, offset=0)

    assert total == 2
    assert [loan.id for loan in items] == [first.id, second.id]


def test_list_loans_filters_by_member_book_and_open_only(db_session: Session) -> None:
    today = date(2024, 5, 1)
    book_a = _book(db_session, "isbn-a", "Book A")
    book_b = _book(db_session, "isbn-b", "Book B")
    member_a = _member(db_session, "a@example.com", "A")
    member_b = _member(db_session, "b@example.com", "B")
    open_loan = _loan(db_session, book_a, member_a, today, today + timedelta(days=14))
    _loan(
        db_session,
        book_a,
        member_b,
        today,
        today + timedelta(days=14),
        returned_on=today,
    )
    other_open = _loan(db_session, book_b, member_a, today, today + timedelta(days=14))
    db_session.commit()

    member_items, member_total = list_loans(db_session, member_id=member_a.id)
    assert member_total == 2
    assert {loan.id for loan in member_items} == {open_loan.id, other_open.id}

    book_items, book_total = list_loans(db_session, book_id=book_a.id)
    assert book_total == 2
    assert all(loan.book_id == book_a.id for loan in book_items)

    open_items, open_total = list_loans(db_session, book_id=book_a.id, open_only=True)
    assert open_total == 1
    assert [loan.id for loan in open_items] == [open_loan.id]

    combined_items, combined_total = list_loans(
        db_session, member_id=member_a.id, book_id=book_a.id, open_only=True
    )
    assert combined_total == 1
    assert [loan.id for loan in combined_items] == [open_loan.id]


def test_list_loans_total_counts_before_pagination(db_session: Session) -> None:
    today = date(2024, 5, 1)
    book = _book(db_session, "isbn-page")
    member = _member(db_session, "page@example.com")
    for _ in range(5):
        _loan(db_session, book, member, today, today + timedelta(days=14))
    db_session.commit()

    items, total = list_loans(db_session, book_id=book.id, limit=2, offset=1)

    assert total == 5
    assert len(items) == 2


def test_list_overdue_selects_only_open_loans_due_before_today(
    db_session: Session,
) -> None:
    today = date(2024, 5, 15)
    book = _book(db_session, "isbn-overdue", "Overdue Book")
    member = _member(db_session, "overdue@example.com", "Overdue Member")

    overdue = _loan(
        db_session,
        book,
        member,
        today - timedelta(days=20),
        today - timedelta(days=5),
    )
    due_today = _loan(db_session, book, member, today, today)
    future = _loan(db_session, book, member, today, today + timedelta(days=14))
    returned = _loan(
        db_session,
        book,
        member,
        today - timedelta(days=30),
        today - timedelta(days=10),
        returned_on=today - timedelta(days=8),
    )
    db_session.commit()

    items, total = list_overdue(db_session, today)

    assert total == len(items)
    returned_ids = {loan.id for loan in items}
    assert overdue.id in returned_ids
    assert due_today.id not in returned_ids
    assert future.id not in returned_ids
    assert returned.id not in returned_ids

    entry = next(loan for loan in items if loan.id == overdue.id)
    assert entry.days_overdue == 5
    assert entry.book.title == "Overdue Book"
    assert entry.book.author == "Author"
    assert entry.book.isbn == "isbn-overdue"
    assert entry.member.name == "Overdue Member"
    assert entry.member.email == "overdue@example.com"
    assert entry.returned_on is None


def _router_client(db_session: Session) -> TestClient:
    """Client over a minimal app that mounts only this ticket's router.

    The loan-report paths are mounted on their own here so the assertions do not
    depend on whether the loan-creation ticket has already dropped its temporary
    ``GET /loans`` stub from ``app/routers/loans.py``.
    """
    application = FastAPI()
    application.include_router(loan_reports.router)
    application.dependency_overrides[get_db] = lambda: db_session
    return TestClient(application)


def test_list_loans_route_serves_filtered_page(db_session: Session) -> None:
    today = date(2024, 5, 1)
    book = _book(db_session, "isbn-route")
    member = _member(db_session, "route@example.com")
    _loan(db_session, book, member, today, today + timedelta(days=14))
    db_session.commit()

    client = _router_client(db_session)
    response = client.get("/loans", params={"member_id": member.id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    assert len(payload["items"]) == 1


def test_list_loans_route_registered_on_app(client, db_session: Session) -> None:
    today = date(2024, 5, 1)
    book = _book(db_session, "isbn-on-app")
    member = _member(db_session, "on-app@example.com")
    seeded = _loan(db_session, book, member, today, today + timedelta(days=14))
    db_session.commit()

    response = client.get("/loans", params={"book_id": book.id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    assert any(item["id"] == seeded.id for item in payload["items"])


def test_list_overdue_route_is_wired(client, db_session: Session) -> None:
    today = datetime.now(UTC).date()
    book = _book(db_session, "isbn-route-overdue")
    member = _member(db_session, "route-overdue@example.com")
    overdue = _loan(
        db_session,
        book,
        member,
        today - timedelta(days=20),
        today - timedelta(days=5),
    )
    db_session.commit()

    response = client.get("/loans/overdue")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == len(payload["items"])
    entry = next(item for item in payload["items"] if item["id"] == overdue.id)
    assert entry["days_overdue"] == 5
    assert entry["book"]["isbn"] == "isbn-route-overdue"
    assert entry["member"]["email"] == "route-overdue@example.com"
