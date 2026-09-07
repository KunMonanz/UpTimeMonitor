import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import TypeAdapter

from app.dependencies import (
    AccessibleURLMonitor,
    CurrentUser,
    ManageableURLMonitor,
    get_group_repo,
    get_url_monitor_repo,
)
from app.errors.group_errors import GroupDoesNotExistError, UserNotGroupAdminError
from app.errors.url_monitor_errors import DuplicateURLMonitorForOwner
from app.repositories.group_repository import GroupRepository
from app.repositories.url_monitor_repository import URLMonitorRepository
from app.routes.cache_keys import (
    get_monitor_cache_key,
    get_monitor_lists_cache_key,
    invalidate_monitor_caches,
    invalidate_monitor_list_caches,
)
from app.routes.openapi_responses import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
)
from app.schemas.monitor_url_schemas import (
    MonitorUrlCreate,
    MonitorUrlResponse,
    MonitorUrlUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.services.redis_client import redis_client

router = APIRouter(prefix="/api/v1/monitors", tags=["Monitor URL"])
logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model=MonitorUrlResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **CONFLICT_RESPONSE,
    },
)
async def create_monitor_url(
    payload: MonitorUrlCreate,
    current_user: CurrentUser,
    url_monitor_repo: Annotated[URLMonitorRepository, Depends(get_url_monitor_repo)],
    group_repo: Annotated[GroupRepository, Depends(get_group_repo)],
):
    """Create a new URL monitor entry."""
    logger.info("INFO: Attempting to create a new URL monitor entry")

    if payload.group_id is None:
        try:
            new_url_monitor = await url_monitor_repo.add_user_owned_url(
                payload.url, user_id=current_user.id
            )
        except DuplicateURLMonitorForOwner as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        await invalidate_monitor_list_caches([current_user.id])
    else:
        try:
            group = await group_repo.ensure_group_admin(
                payload.group_id, current_user.id
            )
        except GroupDoesNotExistError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except UserNotGroupAdminError as exc:
            raise HTTPException(status_code=403, detail=str(exc))

        try:
            new_url_monitor = await url_monitor_repo.add_group_owned_url(
                payload.url, group_id=group.id
            )
        except DuplicateURLMonitorForOwner as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        await invalidate_monitor_list_caches(
            [member.id for member in group.members]
            + [admin.id for admin in group.admins]
        )

    logger.info(f"SUCCESS: Created new URL monitor entry with ID: {new_url_monitor.id}")
    return new_url_monitor


@router.get(
    "/",
    response_model=PaginatedResponse[MonitorUrlResponse],
    responses={**UNAUTHORIZED_RESPONSE},
)
async def get_all_monitor_urls(
    current_user: CurrentUser,
    url_monitor_repo: Annotated[URLMonitorRepository, Depends(get_url_monitor_repo)],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Retrieve paginated URL monitor entries accessible to the current user."""
    logger.info("INFO: Attempting to return accessible URL monitor entries")

    cache_key = await get_monitor_lists_cache_key(current_user.id, offset, limit)
    cached_data = await redis_client.get(cache_key)

    if cached_data:
        logger.info("SUCCESS: Returned cached accessible URL monitor entries")
        return Response(content=cached_data, media_type="application/json")

    url_monitors, total = await url_monitor_repo.get_all_accessible_urls(
        current_user.id, offset=offset, limit=limit
    )

    item_adapter = TypeAdapter(list[MonitorUrlResponse])
    items = item_adapter.validate_python(url_monitors, from_attributes=True)
    response_payload = PaginatedResponse[MonitorUrlResponse](
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )
    json_data = response_payload.model_dump_json()

    await redis_client.set(cache_key, json_data, ex=180)

    logger.info("SUCCESS: Returned accessible URL monitor entries")
    return response_payload


@router.get(
    "/{url_id}",
    response_model=MonitorUrlResponse,
    responses={**UNAUTHORIZED_RESPONSE, **NOT_FOUND_RESPONSE},
)
async def get_monitor_url(url_monitor: AccessibleURLMonitor):
    """Retrieve a specific URL monitor entry by its ID."""
    cache_key = await get_monitor_cache_key(url_monitor.id)
    cached_data = await redis_client.get(cache_key)

    if cached_data:
        logger.info("SUCCESS: Returned URL monitor entry")
        return Response(content=cached_data, media_type="application/json")

    ta = TypeAdapter(MonitorUrlResponse)
    response_data = ta.validate_python(url_monitor, from_attributes=True)
    json_data = ta.dump_json(response_data)

    await redis_client.set(cache_key, json_data, ex=180)
    logger.info("SUCCESS: Returned URL monitor entry")

    return url_monitor


@router.patch(
    "/{url_id}",
    response_model=MonitorUrlResponse,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **CONFLICT_RESPONSE,
    },
)
async def update_monitor_url(
    payload: MonitorUrlUpdate,
    url_monitor: ManageableURLMonitor,
    url_monitor_repo: Annotated[URLMonitorRepository, Depends(get_url_monitor_repo)],
):
    """Update a specific URL monitor entry by its ID."""
    try:
        updated_monitor = await url_monitor_repo.update_url(
            url_id=url_monitor.id, url=payload.url
        )
    except DuplicateURLMonitorForOwner as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if updated_monitor is None:
        raise HTTPException(status_code=404, detail="URL monitor not found")

    await invalidate_monitor_caches(url_monitor)
    logger.info(f"SUCCESS: Updated URL monitor entry with ID: {updated_monitor.id}")
    return updated_monitor


@router.delete(
    "/{url_id}",
    responses={**UNAUTHORIZED_RESPONSE, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
async def delete_monitor_url(
    url_monitor: ManageableURLMonitor,
    url_monitor_repo: Annotated[URLMonitorRepository, Depends(get_url_monitor_repo)],
):
    deleted = await url_monitor_repo.delete_url(url_monitor.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="URL monitor not found")

    await invalidate_monitor_caches(url_monitor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
