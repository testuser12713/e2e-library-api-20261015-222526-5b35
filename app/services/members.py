"""Member CRUD service.

Every function works on a SQLAlchemy session handed in by the caller and signals
failures through :class:`AppError` so the shared handlers build the unified error
body. E-mail addresses are stored normalised (lower case), which the schemas
enforce, so a duplicate is detected regardless of casing.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Loan, Member
from app.schemas.members import MemberCreate, MemberPatch


def _get_or_404(db: Session, member_id: int) -> Member:
    member = db.get(Member, member_id)
    if member is None:
        raise AppError(
            status_code=404,
            code="not_found",
            message=f"Member {member_id} not found",
        )
    return member


def _email_taken(db: Session, email: str, exclude_id: int | None = None) -> bool:
    stmt = select(Member.id).where(func.lower(Member.email) == email.lower())
    if exclude_id is not None:
        stmt = stmt.where(Member.id != exclude_id)
    return db.execute(stmt).first() is not None


def _duplicate_email(email: str) -> AppError:
    return AppError(
        status_code=409,
        code="conflict",
        message="A member with this e-mail already exists",
        details=[{"field": "email", "message": "already exists"}],
    )


def _commit(db: Session, member: Member) -> Member:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate_email(member.email) from exc
    db.refresh(member)
    return member


def create_member(db: Session, payload: MemberCreate) -> Member:
    """Create a member; a duplicate e-mail (any casing) raises a 409 conflict."""
    if _email_taken(db, payload.email):
        raise _duplicate_email(payload.email)
    member = Member(
        name=payload.name,
        email=payload.email,
        member_since=payload.member_since,
    )
    db.add(member)
    return _commit(db, member)


def list_members(db: Session, limit: int, offset: int) -> tuple[list[Member], int]:
    """Return a stable page of members plus the total number of rows."""
    total = db.execute(select(func.count()).select_from(Member)).scalar_one()
    members = list(
        db.execute(select(Member).order_by(Member.id).limit(limit).offset(offset)).scalars()
    )
    return members, total


def get_member(db: Session, member_id: int) -> Member:
    """Return one member or raise a 404."""
    return _get_or_404(db, member_id)


def replace_member(db: Session, member_id: int, payload: MemberCreate) -> Member:
    """Full replacement of the mutable fields of a member."""
    member = _get_or_404(db, member_id)
    if _email_taken(db, payload.email, exclude_id=member_id):
        raise _duplicate_email(payload.email)
    member.name = payload.name
    member.email = payload.email
    member.member_since = payload.member_since
    return _commit(db, member)


def patch_member(db: Session, member_id: int, payload: MemberPatch) -> Member:
    """Update only the fields actually supplied; ``None`` means unchanged."""
    member = _get_or_404(db, member_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("email") is not None and _email_taken(db, data["email"], exclude_id=member_id):
        raise _duplicate_email(data["email"])
    for field, value in data.items():
        if value is not None:
            setattr(member, field, value)
    return _commit(db, member)


def delete_member(db: Session, member_id: int) -> None:
    """Delete a member; a member with open loans raises a 409 conflict."""
    member = _get_or_404(db, member_id)
    open_loans = db.execute(
        select(func.count())
        .select_from(Loan)
        .where(Loan.member_id == member_id, Loan.returned_on.is_(None))
    ).scalar_one()
    if open_loans:
        raise AppError(
            status_code=409,
            code="conflict",
            message="Member has open loans and cannot be deleted",
            details=[{"field": "member_id", "message": "open loans exist"}],
        )
    db.delete(member)
    db.commit()
