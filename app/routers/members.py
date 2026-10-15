"""Member routes: CRUD over the member resource."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.members import MemberCreate, MemberList, MemberPatch, MemberRead
from app.security import require_api_key
from app.services import members as members_service

router = APIRouter(tags=["members"])


@router.post(
    "/members",
    response_model=MemberRead,
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
def create_member(payload: MemberCreate, db: Session = Depends(get_db)) -> MemberRead:
    member = members_service.create_member(db, payload)
    return MemberRead.model_validate(member)


@router.get("/members", response_model=MemberList)
def list_members(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> MemberList:
    members, total = members_service.list_members(db, limit, offset)
    return MemberList(
        items=[MemberRead.model_validate(member) for member in members],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/members/{member_id}", response_model=MemberRead)
def get_member(member_id: int, db: Session = Depends(get_db)) -> MemberRead:
    member = members_service.get_member(db, member_id)
    return MemberRead.model_validate(member)


@router.put(
    "/members/{member_id}",
    response_model=MemberRead,
    dependencies=[Depends(require_api_key)],
)
def replace_member(
    member_id: int,
    payload: MemberCreate,
    db: Session = Depends(get_db),
) -> MemberRead:
    member = members_service.replace_member(db, member_id, payload)
    return MemberRead.model_validate(member)


@router.patch(
    "/members/{member_id}",
    response_model=MemberRead,
    dependencies=[Depends(require_api_key)],
)
def update_member(
    member_id: int,
    payload: MemberPatch,
    db: Session = Depends(get_db),
) -> MemberRead:
    member = members_service.patch_member(db, member_id, payload)
    return MemberRead.model_validate(member)


@router.delete(
    "/members/{member_id}",
    status_code=204,
    dependencies=[Depends(require_api_key)],
)
def delete_member(member_id: int, db: Session = Depends(get_db)) -> None:
    members_service.delete_member(db, member_id)
