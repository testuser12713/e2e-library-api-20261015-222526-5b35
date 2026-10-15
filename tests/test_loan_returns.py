"""Tests for loan return (AC-10 and AC-11)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Book, Loan, Member


def _today() -> date:
    return datetime.now(UTC).date()


def _seed_book(db: Session, *, isbn: str, copies_total: int = 3, copies_available: int = 2) -> Book:
    book = Book(
        title="Returnable",
        author="Tester",
        isbn=isbn,
        publication_year=2000,
        copies_total=copies_total,
        copies_available=copies_available,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def _seed_member(db: Session, *, email: str) -> Member:
    member = Member(name="Returner", email=email, member_since=date(2020, 1, 1))
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def _seed_loan(db: Session, book: Book, member: Member, *, returned_on: date | None = None) -> Loan:
    loan = Loan(
        book_id=book.id,
        member_id=member.id,
        loaned_on=date(2024, 1, 1),
        due_on=date(2024, 1, 15),
        returned_on=returned_on,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def test_return_open_loan_sets_today_and_frees_copy(
    client: TestClient, db_session: Session
) -> None:
    book = _seed_book(db_session, isbn="return-open-1", copies_available=2)
    member = _seed_member(db_session, email="return-open-1@example.com")
    loan = _seed_loan(db_session, book, member)

    response = client.post(f"/loans/{loan.id}/return", headers={"X-API-Key": "test-api-key"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == loan.id
    assert body["returned_on"] == _today().isoformat()

    db_session.expire_all()
    assert db_session.get(Loan, loan.id).returned_on == _today()
    assert db_session.get(Book, book.id).copies_available == 3


def test_return_unknown_loan_returns_404(client: TestClient) -> None:
    response = client.post("/loans/999999/return", headers={"X-API-Key": "test-api-key"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_second_return_conflicts_without_changing_date(
    client: TestClient, db_session: Session
) -> None:
    book = _seed_book(db_session, isbn="return-twice-1", copies_available=1)
    member = _seed_member(db_session, email="return-twice-1@example.com")
    already_returned = date(2024, 6, 6)
    loan = _seed_loan(db_session, book, member, returned_on=already_returned)

    response = client.post(f"/loans/{loan.id}/return", headers={"X-API-Key": "test-api-key"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"

    db_session.expire_all()
    assert db_session.get(Loan, loan.id).returned_on == already_returned
    assert db_session.get(Book, book.id).copies_available == 1


def test_return_twice_via_endpoint_frees_metadata_once(
    client: TestClient, db_session: Session
) -> None:
    book = _seed_book(db_session, isbn="return-flow-1", copies_available=1)
    member = _seed_member(db_session, email="return-flow-1@example.com")
    loan = _seed_loan(db_session, book, member)

    first = client.post(f"/loans/{loan.id}/return", headers={"X-API-Key": "test-api-key"})
    second = client.post(f"/loans/{loan.id}/return", headers={"X-API-Key": "test-api-key"})

    assert first.status_code == 200
    assert second.status_code == 409

    db_session.expire_all()
    assert db_session.get(Book, book.id).copies_available == 2
    assert db_session.get(Loan, loan.id).returned_on == _today()


def test_due_arithmetic_unchanged_on_return(client: TestClient, db_session: Session) -> None:
    book = _seed_book(db_session, isbn="return-due-1")
    member = _seed_member(db_session, email="return-due-1@example.com")
    loan = _seed_loan(db_session, book, member)
    due = loan.due_on

    response = client.post(f"/loans/{loan.id}/return", headers={"X-API-Key": "test-api-key"})

    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(Loan, loan.id).due_on == due
    assert db_session.get(Loan, loan.id).returned_on == _today()
