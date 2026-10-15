"""Request and response models for books.

Includes the domain validators for the book feature: ISBN-10/ISBN-13 checksum,
the publication-year range and a positive copy count. Invalid input raises a
:class:`pydantic.ValidationError`, which the shared handler turns into a 422
response that names the offending field.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

MIN_PUBLICATION_YEAR = 1450


def normalize_isbn(value: str) -> str:
    """Return the canonical form of an ISBN (no hyphens/spaces, upper case)."""
    return value.replace("-", "").replace(" ", "").upper()


def _is_valid_isbn10(isbn: str) -> bool:
    if len(isbn) != 10 or not isbn[:9].isdigit():
        return False
    last = isbn[9]
    if last == "X":
        check = 10
    elif last.isdigit():
        check = int(last)
    else:
        return False
    total = sum((10 - index) * int(char) for index, char in enumerate(isbn[:9])) + check
    return total % 11 == 0


def _is_valid_isbn13(isbn: str) -> bool:
    if len(isbn) != 13 or not isbn.isdigit():
        return False
    total = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(isbn))
    return total % 10 == 0


def validate_isbn(value: str) -> str:
    """Validate an ISBN-10/ISBN-13 checksum and return its canonical form."""
    normalized = normalize_isbn(value)
    if _is_valid_isbn10(normalized) or _is_valid_isbn13(normalized):
        return normalized
    raise ValueError("isbn must be a valid ISBN-10 or ISBN-13")


def _validate_publication_year(value: int) -> int:
    current_year = date.today().year
    if value < MIN_PUBLICATION_YEAR or value > current_year:
        raise ValueError(
            f"publication_year must be between {MIN_PUBLICATION_YEAR} and {current_year}"
        )
    return value


def _validate_copies_total(value: int) -> int:
    if value < 1:
        raise ValueError("copies_total must be at least 1")
    return value


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    publication_year: int
    copies_total: int

    @field_validator("isbn")
    @classmethod
    def _check_isbn(cls, value: str) -> str:
        return validate_isbn(value)

    @field_validator("publication_year")
    @classmethod
    def _check_year(cls, value: int) -> int:
        return _validate_publication_year(value)

    @field_validator("copies_total")
    @classmethod
    def _check_copies(cls, value: int) -> int:
        return _validate_copies_total(value)


class BookPatch(BaseModel):
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    publication_year: int | None = None
    copies_total: int | None = None

    @field_validator("isbn")
    @classmethod
    def _check_isbn(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_isbn(value)

    @field_validator("publication_year")
    @classmethod
    def _check_year(cls, value: int | None) -> int | None:
        if value is None:
            return value
        return _validate_publication_year(value)

    @field_validator("copies_total")
    @classmethod
    def _check_copies(cls, value: int | None) -> int | None:
        if value is None:
            return value
        return _validate_copies_total(value)


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
