"""Book routes: CRUD with search, pagination and validation."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.books import BookCreate, BookList, BookPatch, BookRead
from app.security import require_api_key
from app.services import books as books_service

router = APIRouter(tags=["books"])


@router.post(
    "/books",
    response_model=BookRead,
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
def create_book(payload: BookCreate, db: Session = Depends(get_db)) -> BookRead:
    return BookRead.model_validate(books_service.create_book(db, payload))


@router.get("/books", response_model=BookList)
def list_books(
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> BookList:
    items, total = books_service.list_books(db, q=q, limit=limit, offset=offset)
    return BookList(
        items=[BookRead.model_validate(book) for book in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/books/{book_id}", response_model=BookRead)
def get_book(book_id: int, db: Session = Depends(get_db)) -> BookRead:
    return BookRead.model_validate(books_service.get_book(db, book_id))


@router.put(
    "/books/{book_id}",
    response_model=BookRead,
    dependencies=[Depends(require_api_key)],
)
def replace_book(book_id: int, payload: BookCreate, db: Session = Depends(get_db)) -> BookRead:
    return BookRead.model_validate(books_service.replace_book(db, book_id, payload))


@router.patch(
    "/books/{book_id}",
    response_model=BookRead,
    dependencies=[Depends(require_api_key)],
)
def update_book(book_id: int, payload: BookPatch, db: Session = Depends(get_db)) -> BookRead:
    return BookRead.model_validate(books_service.update_book(db, book_id, payload))


@router.delete(
    "/books/{book_id}",
    status_code=204,
    dependencies=[Depends(require_api_key)],
)
def delete_book(book_id: int, db: Session = Depends(get_db)) -> None:
    books_service.delete_book(db, book_id)
