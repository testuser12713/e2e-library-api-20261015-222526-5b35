"""Book routes — stubs until the book CRUD ticket fills them."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.errors import AppError
from app.schemas.books import BookCreate, BookList, BookPatch, BookRead
from app.security import require_api_key

router = APIRouter(tags=["books"])


def _not_implemented() -> AppError:
    return AppError(
        status_code=501,
        code="not_implemented",
        message="Book routes are implemented by the book CRUD ticket.",
    )


@router.post(
    "/books",
    response_model=BookRead,
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
def create_book(payload: BookCreate) -> BookRead:
    raise _not_implemented()


@router.get("/books", response_model=BookList)
def list_books(
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> BookList:
    raise _not_implemented()


@router.get("/books/{book_id}", response_model=BookRead)
def get_book(book_id: int) -> BookRead:
    raise _not_implemented()


@router.put(
    "/books/{book_id}",
    response_model=BookRead,
    dependencies=[Depends(require_api_key)],
)
def replace_book(book_id: int, payload: BookCreate) -> BookRead:
    raise _not_implemented()


@router.patch(
    "/books/{book_id}",
    response_model=BookRead,
    dependencies=[Depends(require_api_key)],
)
def update_book(book_id: int, payload: BookPatch) -> BookRead:
    raise _not_implemented()


@router.delete(
    "/books/{book_id}",
    status_code=204,
    dependencies=[Depends(require_api_key)],
)
def delete_book(book_id: int) -> None:
    raise _not_implemented()
