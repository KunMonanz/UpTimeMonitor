from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.dependencies import CurrentUser, get_group_repo
from app.errors.group_errors import (
    GroupDoesNotExistError,
    UserNotGroupAdminError,
    UserNotGroupMemberError,
)
from app.errors.user_errors import UserDoesNotExist
from app.repositories.group_repository import GroupRepository
from app.schemas.group_schema import GroupCreate, GroupResponse

router = APIRouter(prefix="/api/v1/groups", tags=["Groups"])


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group_route(
    payload: GroupCreate,
    current_user: CurrentUser,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
):
    try:
        return await group_repo.create_group(
            name=payload.name,
            description=payload.description,
            user_id=current_user.id,
        )
    except UserDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Group already exists",
        )


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group_route(
    group_id: UUID,
    current_user: CurrentUser,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
):
    try:
        return await group_repo.get_group_by_id(
            group_id=group_id, user_id=current_user.id
        )
    except UserDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    except UserNotGroupMemberError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this group",
        )
    except GroupDoesNotExistError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_route(
    group_id: UUID,
    current_user: CurrentUser,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
):
    try:
        await group_repo.delete_group(group_id=group_id, admin_id=current_user.id)
    except UserDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    except UserNotGroupAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not an admin of this group",
        )
    except GroupDoesNotExistError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
