"""Tests for the skeleton itself: health, docs and the unified error body."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.errors import AppError, register_exception_handlers


class _Payload(BaseModel):
    title: str


def _isolated_app() -> FastAPI:
    """A throwaway app wiring only the shared exception handlers.

    Used to exercise the error contract without asserting the temporary answer
    of any stub route.
    """
    test_app = FastAPI()
    register_exception_handlers(test_app)
    return test_app


def test_health_without_api_key(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_interactive_docs_available(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200


def test_unknown_path_uses_unified_error_body(client: TestClient) -> None:
    response = client.get("/no-such-route")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["details"] == []


def test_app_error_uses_unified_error_body() -> None:
    test_app = _isolated_app()

    @test_app.get("/boom")
    def boom() -> None:
        raise AppError(
            status_code=409,
            code="conflict",
            message="duplicate isbn",
            details=[{"field": "isbn", "message": "already exists"}],
        )

    with TestClient(test_app) as isolated_client:
        response = isolated_client.get("/boom")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "conflict",
            "message": "duplicate isbn",
            "details": [{"field": "isbn", "message": "already exists"}],
        }
    }


def test_app_error_without_details_defaults_to_empty_list() -> None:
    test_app = _isolated_app()

    @test_app.get("/boom")
    def boom() -> None:
        raise AppError(status_code=404, code="not_found", message="book not found")

    with TestClient(test_app) as isolated_client:
        response = isolated_client.get("/boom")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "book not found", "details": []}
    }


def test_validation_error_uses_unified_error_body() -> None:
    test_app = _isolated_app()

    @test_app.post("/typed")
    def typed(payload: _Payload) -> dict[str, str]:
        return {"title": payload.title}

    with TestClient(test_app) as isolated_client:
        response = isolated_client.post("/typed", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]
    assert body["error"]["details"][0]["field"] == "title"
    assert "message" in body["error"]["details"][0]
