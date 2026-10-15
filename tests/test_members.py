"""Tests for the member CRUD endpoints and the e-mail uniqueness rule."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Book, Loan, Member


def _headers() -> dict[str, str]:
    return {"X-API-Key": settings.library_api_key or ""}


def _unique_email(prefix: str = "member") -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def _create_member(client: TestClient, email: str | None = None, name: str = "Ada") -> dict:
    response = client.post(
        "/members",
        json={
            "name": name,
            "email": email or _unique_email(),
            "member_since": "2024-01-01",
        },
        headers=_headers(),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_member_shows_in_list_and_get(client: TestClient) -> None:
    email = _unique_email("ada")
    created = _create_member(client, email=email)

    assert created["id"] > 0
    assert created["email"] == email
    assert created["member_since"] == "2024-01-01"

    listed = client.get("/members")
    assert listed.status_code == 200
    body = listed.json()
    ids = [item["id"] for item in body["items"]]
    assert created["id"] in ids
    assert isinstance(body["total"], int)
    assert body["limit"] == 50
    assert body["offset"] == 0

    fetched = client.get(f"/members/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_duplicate_email_in_different_casing_is_conflict(client: TestClient) -> None:
    email = _unique_email("case")
    _create_member(client, email=email)

    response = client.post(
        "/members",
        json={
            "name": "Second",
            "email": email.upper(),
            "member_since": "2024-02-02",
        },
        headers=_headers(),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "conflict"
    fields = [detail["field"] for detail in body["error"]["details"]]
    assert "email" in fields


def test_malformed_email_is_validation_error(client: TestClient) -> None:
    response = client.post(
        "/members",
        json={"name": "Bad", "email": "not-an-email", "member_since": "2024-01-01"},
        headers=_headers(),
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    fields = [detail["field"] for detail in body["error"]["details"]]
    assert "email" in fields


def test_email_is_normalised_to_lowercase(client: TestClient) -> None:
    mixed = f"MiXeD-{uuid4().hex}@Example.COM"
    created = _create_member(client, email=mixed)
    assert created["email"] == mixed.lower()


def test_get_unknown_member_returns_404(client: TestClient) -> None:
    response = client.get("/members/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_replace_member(client: TestClient) -> None:
    created = _create_member(client)
    new_email = _unique_email("replaced")

    response = client.put(
        f"/members/{created['id']}",
        json={"name": "Grace", "email": new_email, "member_since": "2020-05-05"},
        headers=_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Grace"
    assert body["email"] == new_email
    assert body["member_since"] == "2020-05-05"


def test_replace_unknown_member_returns_404(client: TestClient) -> None:
    response = client.put(
        "/members/999999",
        json={"name": "X", "email": _unique_email(), "member_since": "2020-05-05"},
        headers=_headers(),
    )
    assert response.status_code == 404


def test_patch_member_updates_only_given_fields(client: TestClient) -> None:
    created = _create_member(client, name="Original")
    other = _create_member(client)

    response = client.patch(
        f"/members/{created['id']}", json={"name": "Patched"}, headers=_headers()
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Patched"
    assert body["email"] == created["email"]

    clash = client.patch(
        f"/members/{created['id']}",
        json={"email": other["email"].upper()},
        headers=_headers(),
    )
    assert clash.status_code == 409


def test_patch_unknown_member_returns_404(client: TestClient) -> None:
    response = client.patch("/members/999999", json={"name": "X"}, headers=_headers())
    assert response.status_code == 404


def test_delete_member_then_get_returns_404(client: TestClient) -> None:
    created = _create_member(client)

    response = client.delete(f"/members/{created['id']}", headers=_headers())
    assert response.status_code == 204

    assert client.get(f"/members/{created['id']}").status_code == 404


def test_delete_unknown_member_returns_404(client: TestClient) -> None:
    response = client.delete("/members/999999", headers=_headers())
    assert response.status_code == 404


def test_delete_member_with_open_loan_is_conflict(client: TestClient, db_session: Session) -> None:
    created = _create_member(client)

    book = Book(
        title="Seeded",
        author="Seeder",
        isbn=uuid4().hex[:13],
        publication_year=2000,
        copies_total=1,
        copies_available=0,
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    loan = Loan(
        book_id=book.id,
        member_id=created["id"],
        loaned_on=date.today(),
        due_on=date.today() + timedelta(days=14),
        returned_on=None,
    )
    db_session.add(loan)
    db_session.commit()

    response = client.delete(f"/members/{created['id']}", headers=_headers())
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"

    still_there = db_session.get(Member, created["id"])
    assert still_there is not None
