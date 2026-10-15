"""Tests for the ``X-API-Key`` guard.

The write routes of the real application are still stubs while their feature
tickets are in flight, so those tests only assert what is true on both sides of
that gap: a guarded route rejects a missing/ wrong key and lets a correct one
through. The "creates no record" half is exercised against a small isolated app
whose guarded write route really persists a row.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.errors import register_exception_handlers
from app.models import Book
from app.schemas.books import BookCreate
from app.security import require_api_key

CONFIGURED_KEY = "unit-test-secret-key"


def _valid_isbn() -> str:
    """A unique, checksum-valid ISBN-13 so the payload passes book validation."""
    body = f"978{uuid.uuid4().int % 10**9:09d}"
    total = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(body))
    return body + str((10 - total % 10) % 10)


def _book_payload() -> dict[str, object]:
    return {
        "title": "Guarded Book",
        "author": "Guard Tester",
        "isbn": _valid_isbn(),
        "publication_year": 2000,
        "copies_total": 1,
    }


def _guarded_app() -> FastAPI:
    """A throwaway app whose guarded write route really persists a book."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.post("/books", status_code=201, dependencies=[Depends(require_api_key)])
    def create_book(payload: BookCreate) -> dict[str, int]:
        db = SessionLocal()
        try:
            book = Book(
                title=payload.title,
                author=payload.author,
                isbn=payload.isbn,
                publication_year=payload.publication_year,
                copies_total=payload.copies_total,
                copies_available=payload.copies_total,
            )
            db.add(book)
            db.commit()
            db.refresh(book)
            return {"id": book.id}
        finally:
            db.close()

    return test_app


def _book_count(db: Session) -> int:
    return db.query(Book).count()


@pytest.fixture()
def configured_key(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("LIBRARY_API_KEY", CONFIGURED_KEY)
    return CONFIGURED_KEY


def test_write_without_key_is_rejected_and_creates_no_record(
    db_session: Session, configured_key: str
) -> None:
    before = _book_count(db_session)
    with TestClient(_guarded_app()) as client:
        response = client.post("/books", json=_book_payload())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert response.json()["error"]["details"] == []
    db_session.rollback()
    assert _book_count(db_session) == before


def test_write_with_wrong_key_is_rejected_and_creates_no_record(
    db_session: Session, configured_key: str
) -> None:
    before = _book_count(db_session)
    with TestClient(_guarded_app()) as client:
        response = client.post("/books", json=_book_payload(), headers={"X-API-Key": "not-the-key"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    db_session.rollback()
    assert _book_count(db_session) == before


def test_write_with_correct_key_passes_guard_and_creates_record(
    db_session: Session, configured_key: str
) -> None:
    before = _book_count(db_session)
    payload = _book_payload()
    with TestClient(_guarded_app()) as client:
        response = client.post("/books", json=payload, headers={"X-API-Key": CONFIGURED_KEY})

    assert response.status_code == 201
    db_session.rollback()
    assert _book_count(db_session) == before + 1

    inserted = db_session.query(Book).filter(Book.isbn == payload["isbn"]).one()
    db_session.delete(inserted)
    db_session.commit()


def test_unset_configured_key_rejects_every_key_without_crashing(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LIBRARY_API_KEY", raising=False)
    before = _book_count(db_session)
    with TestClient(_guarded_app()) as client:
        without_header = client.post("/books", json=_book_payload())
        with_any_header = client.post(
            "/books", json=_book_payload(), headers={"X-API-Key": "anything"}
        )

    assert without_header.status_code == 401
    assert with_any_header.status_code == 401
    assert without_header.json()["error"]["code"] == "unauthorized"
    db_session.rollback()
    assert _book_count(db_session) == before


def _write_requests() -> list[tuple[str, str, dict[str, object] | None]]:
    book = {
        "title": "Old",
        "author": "Writer",
        "isbn": "9783161484100",
        "publication_year": 2000,
        "copies_total": 1,
    }
    member = {"name": "Ann", "email": "ann@example.com", "member_since": "2024-01-01"}
    return [
        ("post", "/books", book),
        ("put", "/books/1", book),
        ("patch", "/books/1", {"title": "New"}),
        ("delete", "/books/1", None),
        ("post", "/members", member),
        ("put", "/members/1", member),
        ("patch", "/members/1", {"name": "New"}),
        ("delete", "/members/1", None),
        ("post", "/loans", {"book_id": 1, "member_id": 1}),
        ("post", "/loans/1/return", None),
    ]


@pytest.mark.parametrize(("method", "path", "body"), _write_requests())
def test_real_write_routes_require_api_key(
    client: TestClient,
    method: str,
    path: str,
    body: dict[str, object] | None,
) -> None:
    response = client.request(method.upper(), path, json=body)

    assert response.status_code == 401, (method, path, response.text)
    assert response.json()["error"]["code"] == "unauthorized"


def test_real_write_route_accepts_configured_key(client: TestClient, configured_key: str) -> None:
    response = client.post(
        "/books",
        json=_book_payload(),
        headers={"X-API-Key": CONFIGURED_KEY},
    )

    assert response.status_code != 401


def test_health_answers_without_key(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "path",
    ["/books", "/books/1", "/members", "/members/1", "/loans", "/loans/overdue"],
)
def test_read_routes_do_not_require_api_key(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code != 401, (path, response.text)
