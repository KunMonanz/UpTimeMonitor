from smtplib import SMTP
from typing import Annotated, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.dependencies import CurrentUser, get_group_repo, get_user_repo
from app.errors.group_errors import (
    GroupDoesNotExistError,
    UserNotGroupAdminError,
    UserNotGroupMemberError,
)
from app.errors.user_errors import UserDoesNotExist
from app.models.users import user_groups
from app.repositories.group_repository import GroupRepository
from app.repositories.user_repository import UserRepository
from app.schemas.group_schema import AddMemberToGroup, GroupCreate, GroupResponse
from app.services.mailer import SMTPEngine, get_email_client
from app.services.token_service import TokenService
from app.utils.email_utils import send_invitation_email

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


@router.post("/{group_id}")
async def send_invitation_route(
    group_id: UUID,
    current_user: CurrentUser,
    payload: AddMemberToGroup,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    smtp_client: Annotated[SMTPEngine, Depends(get_email_client)],
):
    try:
        user = await user_repo.get_user_by_username(payload.email)
        await group_repo.ensure_group_admin(group_id, current_user.id)
        send_invitation_email.delay(
            email=user.email,
            inviter_name=current_user.username,
            token_service=TokenService(prefix="invite"),
            group_id=group_id,
        )
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


@router.get("/accept-invite")
async def accept_invitation_route(
    token: str,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
):
    try:
        token_service = TokenService(prefix="invite")
        identifier = await token_service.verify_token(token, consume=True)
        if identifier is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token",
            )

        email, group_id_str, inviter_id_str = identifier.split(":")
        group_id = UUID(group_id_str)
        inviter_id = UUID(inviter_id_str)

        user = await user_repo.get_user_by_email(email)
        await group_repo.add_user_to_group(
            group_id=group_id, new_member_id=user.id, admin_id=inviter_id
        )

        return {"message": "Successfully joined the group"}
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
    except UserDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
