"""FastAPI application entry point for the library lending API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import validate_settings
from app.database import init_db
from app.errors import register_exception_handlers
from app.routers import (
    books,
    health,
    loan_reports,
    loan_returns,
    loans,
    members,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Validate configuration and create the schema before serving."""
    validate_settings()
    init_db()
    yield


app = FastAPI(
    title="Library Lending API",
    description="REST API for a small city library's lending workflow.",
    version="0.1.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(books.router)
app.include_router(members.router)
app.include_router(loans.router)
app.include_router(loan_returns.router)
app.include_router(loan_reports.router)
