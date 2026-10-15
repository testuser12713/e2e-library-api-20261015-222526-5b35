"""Request and response models for books.

Declarative types only — the domain validators (ISBN checksum, publication year
range, positive copy count) belong to the book feature ticket.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    publication_year: int
    copies_total: int


class BookPatch(BaseModel):
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    publication_year: int | None = None
    copies_total: int | None = None


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    publication_year: int
    copies_total: int
    copies_available: int


class BookList(BaseModel):
    items: list[BookRead]
    total: int
    limit: int
    offset: int
