"""Shared pytest fixtures for the library lending API test-suite.

The suite runs against a single fresh temporary SQLite file per run that is
discarded afterwards. The environment is configured *before* the application is
imported so the engine binds to the temporary database and the startup
validation finds the API key it needs.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from collections.abc import Iterator

import pytest

_TMP_DIR = tempfile.mkdtemp(prefix="library-test-")
atexit.register(shutil.rmtree, _TMP_DIR, ignore_errors=True)
os.environ["LIBRARY_DATABASE_URL"] = f"sqlite:///{os.path.join(_TMP_DIR, 'test.db')}"
os.environ.setdefault("LIBRARY_API_KEY", "test-api-key")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import Base, SessionLocal, engine, get_db, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Iterator[None]:
    """Create every table on the temporary database once per run."""
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session() -> Iterator[Session]:
    """One ORM session against the temporary test database."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """TestClient over the app, with the DB dependency pointing at the test engine."""

    def _override_get_db() -> Iterator[Session]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
