"""Member routes — stubs until the member CRUD ticket fills them."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.errors import AppError
from app.schemas.members import MemberCreate, MemberList, MemberPatch, MemberRead
from app.security import require_api_key

router = APIRouter(tags=["members"])


def _not_implemented() -> AppError:
    return AppError(
        status_code=501,
        code="not_implemented",
        message="Member routes are implemented by the member CRUD ticket.",
    )


@router.post(
    "/members",
    response_model=MemberRead,
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
def create_member(payload: MemberCreate) -> MemberRead:
    raise _not_implemented()


@router.get("/members", response_model=MemberList)
def list_members(limit: int = 50, offset: int = 0) -> MemberList:
    raise _not_implemented()


@router.get("/members/{member_id}", response_model=MemberRead)
def get_member(member_id: int) -> MemberRead:
    raise _not_implemented()


@router.put(
    "/members/{member_id}",
    response_model=MemberRead,
    dependencies=[Depends(require_api_key)],
)
def replace_member(member_id: int, payload: MemberCreate) -> MemberRead:
    raise _not_implemented()


@router.patch(
    "/members/{member_id}",
    response_model=MemberRead,
    dependencies=[Depends(require_api_key)],
)
def update_member(member_id: int, payload: MemberPatch) -> MemberRead:
    raise _not_implemented()


@router.delete(
    "/members/{member_id}",
    status_code=204,
    dependencies=[Depends(require_api_key)],
)
def delete_member(member_id: int) -> None:
    raise _not_implemented()
