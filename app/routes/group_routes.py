from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import TypeAdapter
from sqlalchemy.exc import IntegrityError

from app.config.limiter import enforce_send_cooldown, limiter
from app.config.settings import GROUP_INVITE_COOLDOWN_SECONDS
from app.dependencies import CurrentUser, get_group_repo, get_user_repo
from app.errors.group_errors import (
    GroupDoesNotExistError,
    MonitorNotInGroupError,
    UserNotGroupAdminError,
    UserNotGroupMemberError,
)
from app.errors.url_monitor_errors import (
    DuplicateURLMonitorForOwner,
    URLMonitorDoesNotExist,
)
from app.errors.user_errors import TooManyRequestsError, UserDoesNotExist
from app.models.users import Group
from app.repositories.group_repository import GroupRepository
from app.repositories.user_repository import UserRepository
from app.routes.cache_keys import (
    get_group_cache_key,
    get_group_members_cache_key,
    get_group_monitors_cache_key,
    invalidate_group_caches,
)
from app.routes.openapi_responses import (
    BAD_REQUEST_RESPONSE,
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    TOO_MANY_REQUESTS_RESPONSE,
    UNAUTHORIZED_RESPONSE,
)
from app.schemas.group_schema import AddMemberToGroup, GroupCreate, GroupResponse
from app.schemas.monitor_url_schemas import MonitorUrlCreate, MonitorUrlResponse
from app.schemas.pagination import PaginatedResponse
from app.schemas.user_schema import UserResponse
from app.services.redis_client import redis_client
from app.services.token_service import TokenService
from app.utils.email_utils import send_invitation_email

router = APIRouter(prefix="/api/v1/groups", tags=["Groups"])


def get_group_related_user_ids(group: Group) -> list[UUID]:
    return [member.id for member in group.members] + [
        admin.id for admin in group.admins
    ]


@limiter.limit("10/minute")
@router.post(
    "/",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **CONFLICT_RESPONSE,
        **TOO_MANY_REQUESTS_RESPONSE,
    },
)
async def create_group_route(
    request: Request,
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


@limiter.limit("20/minute")
@router.get(
    "/{group_id}",
    response_model=GroupResponse,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **TOO_MANY_REQUESTS_RESPONSE,
    },
)
async def get_group_route(
    request: Request,
    group_id: UUID,
    current_user: CurrentUser,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
):
    try:
        group = await group_repo.get_group_by_id(
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

    cache_key = await get_group_cache_key(group_id)
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return Response(content=cached_data, media_type="application/json")

    ta = TypeAdapter(GroupResponse)
    response_data = ta.validate_python(group, from_attributes=True)
    json_data = ta.dump_json(response_data)
    await redis_client.set(cache_key, json_data, ex=180)
    return group


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**UNAUTHORIZED_RESPONSE, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
async def delete_group_route(
    group_id: UUID,
    current_user: CurrentUser,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
):
    try:
        group = await group_repo.ensure_group_admin(
            group_id=group_id, admin_id=current_user.id
        )
        affected_user_ids = get_group_related_user_ids(group)
        await group_repo.delete_group(group_id=group_id, admin_id=current_user.id)
        await invalidate_group_caches(group_id, affected_user_ids)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
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


@router.post(
    "/{group_id}/invite",
    responses={
        **UNAUTHORIZED_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **TOO_MANY_REQUESTS_RESPONSE,
    },
)
@limiter.limit("5/hour")
async def send_invitation_route(
    request: Request,
    group_id: UUID,
    current_user: CurrentUser,
    payload: AddMemberToGroup,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
):
    try:
        user = await user_repo.get_user_by_email(payload.email)
        await group_repo.ensure_group_admin(group_id, current_user.id)
        try:
            await enforce_send_cooldown(
                "group-invite",
                f"{group_id}:{user.email}",
                GROUP_INVITE_COOLDOWN_SECONDS,
            )
        except TooManyRequestsError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
                headers={"Retry-After": str(exc.retry_after or 0)},
            )

        await send_invitation_email(
            email=user.email,
            inviter_name=current_user.username,
            token_service=TokenService(prefix="invite"),
            group_id=group_id,
            inviter_id=current_user.id,
        )
        return {"message": "Invitation sent successfully"}
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


@router.get(
    "/invites/accept",
    responses={**BAD_REQUEST_RESPONSE, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
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
        group = await group_repo.get_group_by_id_no_user_check(group_id)
        await invalidate_group_caches(group_id, get_group_related_user_ids(group))

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


@router.get(
    "/{group_id}/monitors",
    response_model=PaginatedResponse[MonitorUrlResponse],
    responses={**UNAUTHORIZED_RESPONSE, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
async def get_group_monitors_route(
    group_id: UUID,
    current_user: CurrentUser,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    try:
        monitors, total = await group_repo.get_group_urls(
            group_id=group_id, user_id=current_user.id, offset=offset, limit=limit
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

    cache_key = await get_group_monitors_cache_key(group_id, offset, limit)
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return Response(content=cached_data, media_type="application/json")

    item_adapter = TypeAdapter(list[MonitorUrlResponse])
    items = item_adapter.validate_python(monitors, from_attributes=True)
    response_payload = PaginatedResponse[MonitorUrlResponse](
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )
    await redis_client.set(cache_key, response_payload.model_dump_json(), ex=180)
    return response_payload


@router.get(
    "/{group_id}/members",
    response_model=PaginatedResponse[UserResponse],
    responses={**UNAUTHORIZED_RESPONSE, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
async def get_group_members_route(
    group_id: UUID,
    current_user: CurrentUser,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    try:
        members, total = await group_repo.get_group_members(
            group_id=group_id, user_id=current_user.id, offset=offset, limit=limit
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

    cache_key = await get_group_members_cache_key(group_id, offset, limit)
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return Response(content=cached_data, media_type="application/json")

    item_adapter = TypeAdapter(list[UserResponse])
    items = item_adapter.validate_python(members, from_attributes=True)
    response_payload = PaginatedResponse[UserResponse](
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )
    await redis_client.set(cache_key, response_payload.model_dump_json(), ex=180)
    return response_payload


@router.delete(
    "/{group_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**UNAUTHORIZED_RESPONSE, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
async def remove_group_member_route(
    group_id: UUID,
    member_id: UUID,
    current_user: CurrentUser,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
):
    try:
        await group_repo.remove_user_from_group(
            group_id=group_id, member_id=member_id, admin_id=current_user.id
        )
        group = await group_repo.get_group_by_id_no_user_check(group_id)
        affected_user_ids = [member_id, *get_group_related_user_ids(group)]
        await invalidate_group_caches(group_id, affected_user_ids)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
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


@router.post(
    "/{group_id}/monitors",
    responses={
        **UNAUTHORIZED_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **CONFLICT_RESPONSE,
    },
)
async def add_group_monitor_route(
    group_id: UUID,
    payload: MonitorUrlCreate,
    current_user: CurrentUser,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
):
    try:
        await group_repo.create_new_monitor_for_group(
            group_id=group_id, url=payload.url, admin_id=current_user.id
        )
        group = await group_repo.get_group_by_id_no_user_check(group_id)
        await invalidate_group_caches(group_id, get_group_related_user_ids(group))
        return {"message": "Monitor added to group successfully"}
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
    except DuplicateURLMonitorForOwner as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.delete(
    "/{group_id}/monitors/{monitor_id}",
    responses={
        **UNAUTHORIZED_RESPONSE,
        **BAD_REQUEST_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **NOT_FOUND_RESPONSE,
    },
)
async def remove_group_monitor_route(
    group_id: UUID,
    monitor_id: UUID,
    current_user: CurrentUser,
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
):
    try:
        await group_repo.delete_monitor_from_group(
            group_id=group_id, monitor_id=monitor_id, admin_id=current_user.id
        )
        group = await group_repo.get_group_by_id_no_user_check(group_id)
        await invalidate_group_caches(group_id, get_group_related_user_ids(group))
        return {"message": "Monitor removed from group successfully"}
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
    except URLMonitorDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found",
        )
    except MonitorNotInGroupError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Monitor is not part of this group",
        )
