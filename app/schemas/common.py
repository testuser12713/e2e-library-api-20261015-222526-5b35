"""Models shared across the API: the error contract, references and health."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody


class BookRef(BaseModel):
    id: int
    title: str
    author: str
    isbn: str


class MemberRef(BaseModel):
    id: int
    name: str
    email: str


class HealthResponse(BaseModel):
    status: str
    database: str
