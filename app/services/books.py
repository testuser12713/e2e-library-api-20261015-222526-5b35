"""Book domain service: create, read, search, replace, patch and delete."""

from __future__ import annotations

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Book, Loan
from app.schemas.books import BookCreate, BookPatch


def _not_found(book_id: int) -> AppError:
    return AppError(
        status_code=404,
        code="not_found",
        message=f"Book {book_id} does not exist.",
        details=[],
    )


def _duplicate_isbn(isbn: str) -> AppError:
    return AppError(
        status_code=409,
        code="conflict",
        message="A book with this ISBN already exists.",
        details=[{"field": "isbn", "message": f"ISBN {isbn} is already in use"}],
    )


def _copies_total_conflict() -> AppError:
    return AppError(
        status_code=429,
        code="conflict",
        message=("copies_total cannot be reduced below the number of copies currently on loan."),
        details=[
            {
                "field": "copies_total",
                "message": "reduction would make copies_available negative",
            }
        ],
    )


def _open_loans_conflict(book_id: int) -> AppError:
    return AppError(
        status_code=409,
        code="conflict",
        message=f"Book {book_id} still has open loans.",
        details=[{"field": "id", "message": "open loans exist"}],
    )


def get_book(db: Session, book_id: int) -> Book:
    """Return the book with ``book_id`` or raise a 404 ``AppError``."""
    book = db.get(Book, book_id)
    if book is None:
        raise _not_found(book_id)
    return book


def _ensure_isbn_free(db: Session, isbn: str, exclude_id: int | None = None) -> None:
    stmt = select(Book.id).where(Book.isbn == isbn)
    if exclude_id is not None:
        stmt = stmt.where(Book.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise _duplicate_isbn(isbn)


def create_book(db: Session, data: BookCreate) -> Book:
    """Persist a new book and return it.

    Raises a 409 ``AppError`` when the ISBN is already taken.
    """
    _ensure_isbn_free(db, data.isbn)
    book = Book(
        title=data.title,
        author=data.author,
        isbn=data.isbn,
        publication_year=data.publication_year,
        copies_total=data.copies_total,
        copies_available=data.copies_total,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def list_books(
    db: Session,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Book], int]:
    """Return one page of books ordered by id and the total match count.

    ``q`` matches a case-insensitive substring of the title OR the author.
    """
    conditions = []
    if q:
        pattern = f"%{q}%"
        conditions.append(or_(Book.title.ilike(pattern), Book.author.ilike(pattern)))

    count_stmt = select(func.count()).select_from(Book)
    list_stmt = select(Book)
    for condition in conditions:
        count_stmt = count_stmt.where(condition)
        list_stmt = list_stmt.where(condition)

    total = db.scalar(count_stmt) or 0
    list_stmt = list_stmt.order_by(Book.id).limit(limit).offset(offset)
    items = list(db.scalars(list_stmt).all())
    return items, total


def replace_book(db: Session, book_id: int, data: BookCreate) -> Book:
    """Replace every mutable field of the book, keeping the copy invariant."""
    book = get_book(db, book_id)
    _ensure_isbn_free(db, data.isbn, exclude_id=book_id)

    new_available = book.copies_available + (data.copies_total - book.copies_total)
    if new_available < 0:
        raise _copies_total_conflict()

    book.title = data.title
    book.author = data.author
    book.isbn = data.isbn
    book.publication_year = data.publication_year
    book.copies_total = data.copies_total
    book.copies_available = new_available
    db.commit()
    db.refresh(book)
    return book


def update_book(db: Session, book_id: int, data: BookPatch) -> Book:
    """Update only the fields explicitly provided in ``data``."""
    book = get_book(db, book_id)
    updates = data.model_dump(exclude_unset=True, exclude_none=True)

    if "isbn" in updates:
        _ensure_isbn_free(db, updates["isbn"], exclude_id=book_id)

    if "copies_total" in updates:
        new_available = book.copies_available + (updates["copies_total"] - book.copies_total)
        if new_available < 0:
            raise _copies_total_conflict()
        book.copies_total = updates["copies_total"]
        book.copies_available = new_available

    for field in ("title", "author", "isbn", "publication_year"):
        if field in updates:
            setattr(book, field, updates[field])

    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, book_id: int) -> None:
    """Delete the book, refusing while it has open loans."""
    book = get_book(db, book_id)
    open_loans = db.scalar(
        select(func.count())
        .select_from(Loan)
        .where(Loan.book_id == book_id, Loan.returned_on.is_(None))
    )
    if open_loans:
        raise _open_loans_conflict(book_id)
    db.execute(delete(Loan).where(Loan.book_id == book_id))
    db.delete(book)
    db.commit()
