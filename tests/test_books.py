"""Tests for the book CRUD slice: validation, search, pagination and conflicts."""

from __future__ import annotations

import itertools
import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Book, Loan, Member

_isbn_counter = itertools.count(1)


def _isbn13() -> str:
    """Return a unique, checksum-valid ISBN-13."""
    body = f"978{next(_isbn_counter):09d}"
    total = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(body))
    return body + str((10 - total % 10) % 10)


def _payload(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "title": "The Test Book",
        "author": "Ada Author",
        "isbn": _isbn13(),
        "publication_year": 2001,
        "copies_total": 3,
    }
    data.update(overrides)
    return data


def _auth() -> dict[str, str]:
    return {"X-API-Key": settings.library_api_key or ""}


def _create_book(client: TestClient, **overrides: object) -> dict:
    response = client.post("/books", json=_payload(**overrides), headers=_auth())
    assert response.status_code == 201, response.text
    return response.json()


def _seed_member(db_session: Session) -> Member:
    member = Member(
        name="Seed Member",
        email=f"seed-{uuid.uuid4()}@example.com",
        member_since=date.today(),
    )
    db_session.add(member)
    db_session.flush()
    return member


def _seed_open_loans(db_session: Session, book_id: int, count: int) -> None:
    member = _seed_member(db_session)
    for _ in range(count):
        db_session.add(
            Loan(
                book_id=book_id,
                member_id=member.id,
                loaned_on=date.today(),
                due_on=date.today() + timedelta(days=14),
                returned_on=None,
            )
        )
    db_session.commit()


def test_create_returns_201_and_get_returns_all_fields(client: TestClient) -> None:
    created = _create_book(client, title="Dune", author="Frank Herbert", copies_total=4)

    assert isinstance(created["id"], int)
    assert created["title"] == "Dune"
    assert created["author"] == "Frank Herbert"
    assert created["publication_year"] == 2001
    assert created["copies_total"] == 4
    assert created["copies_available"] == 4

    response = client.get(f"/books/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_duplicate_isbn_returns_409_and_keeps_existing(client: TestClient) -> None:
    isbn = _isbn13()
    first = _create_book(client, isbn=isbn, title="Original")

    response = client.post("/books", json=_payload(isbn=isbn, title="Clonk"), headers=_auth())
    assert response.status_code == 409
    assert response.json()["error"]["details"][0]["field"] == "isbn"

    unchanged = client.get(f"/books/{first['id']}")
    assert unchanged.status_code == 200
    assert unchanged.json()["title"] == "Original"
    assert unchanged.json()["isbn"] == isbn


def test_get_unknown_book_returns_404(client: TestClient) -> None:
    response = client.get("/books/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_search_matches_title_and_author_case_insensitively(client: TestClient) -> None:
    token = uuid.uuid4().hex[:8]
    by_title = _create_book(client, title=f"Zebra {token}", author="Someone Else")
    by_author = _create_book(client, title="Another Book", author=f"zebra {token}")

    response = client.get("/books", params={"q": f"ZeBrA {token.upper()}"})
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert {by_title["id"], by_author["id"]} <= ids


def test_list_pagination_slices_and_reports_totals(client: TestClient) -> None:
    token = uuid.uuid4().hex[:8]
    created = [_create_book(client, title=f"Paginated {token} #{index}") for index in range(5)]

    first = client.get("/books", params={"q": token, "limit": 2, "offset": 0})
    assert first.status_code == 200
    body = first.json()
    assert body["total"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert [item["id"] for item in body["items"]] == [created[0]["id"], created[1]["id"]]

    second = client.get("/books", params={"q": token, "limit": 2, "offset": 2})
    assert [item["id"] for item in second.json()["items"]] == [
        created[2]["id"],
        created[3]["id"],
    ]


def test_put_replaces_all_fields(client: TestClient) -> None:
    created = _create_book(client, title="Old Title", author="Old Author", copies_total=2)

    replacement = _payload(title="New Title", author="New Author", copies_total=5)
    response = client.put(f"/books/{created['id']}", json=replacement, headers=_auth())
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New Title"
    assert body["author"] == "New Author"
    assert body["isbn"] == replacement["isbn"]
    assert body["copies_total"] == 5
    assert body["copies_available"] == 5


def test_patch_updates_only_given_fields(client: TestClient) -> None:
    created = _create_book(client, title="Keep Title", author="Keep Author")

    response = client.patch(
        f"/books/{created['id']}", json={"title": "Patched Title"}, headers=_auth()
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Patched Title"
    assert body["author"] == "Keep Author"
    assert body["isbn"] == created["isbn"]


def test_patch_duplicate_isbn_returns_409(client: TestClient) -> None:
    first = _create_book(client)
    second = _create_book(client)

    response = client.patch(f"/books/{second['id']}", json={"isbn": first["isbn"]}, headers=_auth())
    assert response.status_code == 409
    assert response.json()["error"]["details"][0]["field"] == "isbn"


def test_patch_copies_total_shifts_available(client: TestClient) -> None:
    created = _create_book(client, copies_total=5)

    reduced = client.patch(f"/books/{created['id']}", json={"copies_total": 3}, headers=_auth())
    assert reduced.status_code == 200
    assert reduced.json()["copies_total"] == 3
    assert reduced.json()["copies_available"] == 3

    raised = client.patch(f"/books/{created['id']}", json={"copies_total": 6}, headers=_auth())
    assert raised.status_code == 200
    assert raised.json()["copies_total"] == 6
    assert raised.json()["copies_available"] == 6


def test_patch_copies_total_below_open_loans_returns_429(
    client: TestClient, db_session: Session
) -> None:
    created = _create_book(client, copies_total=2)
    _seed_open_loans(db_session, created["id"], count=2)
    book = db_session.get(Book, created["id"])
    assert book is not None
    book.copies_available = 0
    db_session.commit()

    response = client.patch(f"/books/{created['id']}", json={"copies_total": 1}, headers=_auth())
    assert response.status_code == 429
    assert response.json()["error"]["details"][0]["field"] == "copies_total"


def test_delete_returns_204_then_get_404(client: TestClient) -> None:
    created = _create_book(client)

    response = client.delete(f"/books/{created['id']}", headers=_auth())
    assert response.status_code == 204
    assert response.content == b""

    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_unknown_book_returns_404(client: TestClient) -> None:
    assert client.delete("/books/999999", headers=_auth()).status_code == 404


def test_delete_with_open_loan_returns_409(client: TestClient, db_session: Session) -> None:
    created = _create_book(client)
    _seed_open_loans(db_session, created["id"], count=1)

    response = client.delete(f"/books/{created['id']}", headers=_auth())
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert client.get(f"/books/{created['id']}").status_code == 200


def test_isbn10_is_accepted_and_normalized(client: TestClient) -> None:
    response = client.post(
        "/books",
        json=_payload(isbn="0-306-40615-2", title="ISBN-10 Book"),
        headers=_auth(),
    )
    assert response.status_code == 201, response.text
    assert response.json()["isbn"] == "0306406152"


def test_invalid_isbn_checksum_returns_422(client: TestClient) -> None:
    response = client.post("/books", json=_payload(isbn="9780306406158"), headers=_auth())
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"][0]["field"] == "isbn"


def test_publication_year_out_of_range_returns_422(client: TestClient) -> None:
    too_old = client.post("/books", json=_payload(publication_year=1400), headers=_auth())
    assert too_old.status_code == 422
    assert too_old.json()["error"]["details"][0]["field"] == "publication_year"

    too_new = client.post(
        "/books", json=_payload(publication_year=date.today().year + 1), headers=_auth()
    )
    assert too_new.status_code == 422
    assert too_new.json()["error"]["details"][0]["field"] == "publication_year"


def test_copies_total_zero_returns_422(client: TestClient) -> None:
    response = client.post("/books", json=_payload(copies_total=0), headers=_auth())
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "copies_total"
