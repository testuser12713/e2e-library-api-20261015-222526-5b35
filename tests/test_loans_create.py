"""Tests for POST /loans: creation, availability and the open-loan limit."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Book, Loan, Member

API_KEY_HEADERS = {"X-API-Key": settings.library_api_key or ""}


def _make_book(db: Session, *, copies_total: int = 1, copies_available: int | None = None) -> Book:
    book = Book(
        title="Loan Test Book",
        author="Loan Test Author",
        isbn=f"isbn-{uuid.uuid4().hex}",
        publication_year=2000,
        copies_total=copies_total,
        copies_available=copies_total if copies_available is None else copies_available,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def _make_member(db: Session) -> Member:
    member = Member(
        name="Loan Test Member",
        email=f"{uuid.uuid4().hex}@example.com",
        member_since=datetime.now(UTC).date(),
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def test_create_loan_returns_201_with_today_and_due_date(
    client: TestClient, db_session: Session
) -> None:
    book = _make_book(db_session, copies_total=2, copies_available=2)
    member = _make_member(db_session)
    today = datetime.now(UTC).date()

    response = client.post(
        "/loans",
        json={"book_id": book.id, "member_id": member.id},
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["book_id"] == book.id
    assert body["member_id"] == member.id
    assert body["loaned_on"] == today.isoformat()
    assert body["due_on"] == (today + timedelta(days=settings.loan_period_days)).isoformat()
    assert body["returned_on"] is None


def test_create_loan_decrements_copies_available(client: TestClient, db_session: Session) -> None:
    book = _make_book(db_session, copies_total=3, copies_available=2)
    member = _make_member(db_session)

    response = client.post(
        "/loans",
        json={"book_id": book.id, "member_id": member.id},
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 201
    db_session.expire_all()
    refreshed = db_session.get(Book, book.id)
    assert refreshed is not None
    assert refreshed.copies_available == 1


def test_create_loan_unknown_book_is_404(client: TestClient, db_session: Session) -> None:
    member = _make_member(db_session)

    response = client.post(
        "/loans",
        json={"book_id": 999_999, "member_id": member.id},
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_create_loan_unknown_member_is_404(client: TestClient, db_session: Session) -> None:
    book = _make_book(db_session)

    response = client.post(
        "/loans",
        json={"book_id": book.id, "member_id": 999_999},
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_create_loan_without_free_copy_is_409(client: TestClient, db_session: Session) -> None:
    book = _make_book(db_session, copies_total=1, copies_available=0)
    member = _make_member(db_session)

    response = client.post(
        "/loans",
        json={"book_id": book.id, "member_id": member.id},
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "conflict"
    assert "free copy" in error["message"].lower()
    assert db_session.query(Loan).filter(Loan.member_id == member.id).count() == 0


def test_fourth_open_loan_answers_409_and_names_the_limit(
    client: TestClient, db_session: Session
) -> None:
    member = _make_member(db_session)
    limit = settings.max_open_loans
    books = [_make_book(db_session) for _ in range(limit + 1)]

    for book in books[:limit]:
        response = client.post(
            "/loans",
            json={"book_id": book.id, "member_id": member.id},
            headers=API_KEY_HEADERS,
        )
        assert response.status_code == 201, response.text

    open_before = (
        db_session.query(Loan)
        .filter(Loan.member_id == member.id, Loan.returned_on.is_(None))
        .count()
    )
    assert open_before == limit

    fourth = client.post(
        "/loans",
        json={"book_id": books[limit].id, "member_id": member.id},
        headers=API_KEY_HEADERS,
    )

    assert fourth.status_code == 409
    error = fourth.json()["error"]
    assert error["code"] == "conflict"
    assert "limit" in error["message"].lower()
    assert str(limit) in error["message"]

    open_after = (
        db_session.query(Loan)
        .filter(Loan.member_id == member.id, Loan.returned_on.is_(None))
        .count()
    )
    assert open_after == limit


def test_returned_loan_does_not_count_towards_the_limit(
    client: TestClient, db_session: Session
) -> None:
    member = _make_member(db_session)
    limit = settings.max_open_loans
    books = [_make_book(db_session) for _ in range(limit + 1)]

    for book in books[:limit]:
        db_session.add(
            Loan(
                book_id=book.id,
                member_id=member.id,
                loaned_on=datetime.now(UTC).date(),
                due_on=datetime.now(UTC).date() + timedelta(days=14),
                returned_on=datetime.now(UTC).date(),
            )
        )
    db_session.commit()

    response = client.post(
        "/loans",
        json={"book_id": books[limit].id, "member_id": member.id},
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 201
