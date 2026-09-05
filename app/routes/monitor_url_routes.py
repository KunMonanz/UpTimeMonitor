import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import TypeAdapter

from app.dependencies import (
    CurrentUser,
    VerifyURLMonitorOwnership,
    get_url_monitor_repo,
)
from app.repositories.url_monitor_repository import URLMonitorRepository
from app.routes.cache_keys import get_monnitor_lists_cache_key
from app.schemas.monitor_url_schemas import (
    MonitorUrlCreate,
    MonitorUrlResponse,
    MonitorUrlUpdate,
)
from app.services.redis_client import redis_client

router = APIRouter(prefix="/api/v1/monitors", tags=["Monitor URL"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=MonitorUrlResponse, status_code=201)
async def create_monitor_url(
    payload: MonitorUrlCreate,
    current_user: CurrentUser,
    url_monitor_repo: Annotated[URLMonitorRepository, Depends(get_url_monitor_repo)],
):
    """Create a new URL monitor entry."""
    logger.info("INFO: Attempting to create a new URL monitor entry")

    new_url_monitor = await url_monitor_repo.add_url(
        payload.url, owner_id=current_user.id
    )
    logger.info(f"SUCCESS: Created new URL monitor entry with ID: {new_url_monitor.id}")
    return new_url_monitor


@router.get("/", response_model=list[MonitorUrlResponse])
async def get_all_monitor_urls(
    current_user: CurrentUser,
    url_monitor_repo: Annotated[URLMonitorRepository, Depends(get_url_monitor_repo)],
):
    """Retrieve all URL monitor entries."""
    logger.info("INFO: Attempting to reurn all URL monitor entries")

    cache_key = get_monnitor_lists_cache_key(current_user.id)
    cached_data = redis_client.get(cache_key)

    if cached_data:
        logger.info("SUCCESS: Returned all URL monitor entries")
        return Response(content=cached_data, media_type="application/json")

    url_monitors = await url_monitor_repo.get_all_user_urls(current_user.id)

    ta = TypeAdapter(list[MonitorUrlResponse])
    json_data = ta.dump_json(url_monitors)

    redis_client.set(cache_key, json_data, ex=180)

    logger.info("SUCCESS: Returned all URL monitor entries")
    return url_monitors


@router.get("/{url_id}", response_model=MonitorUrlResponse)
async def get_monitor_url(url_monitor: VerifyURLMonitorOwnership):
    """Retrieve a specific URL monitor entry by its ID."""

    return url_monitor


@router.patch("/{url_id}", response_model=MonitorUrlResponse)
async def update_monitor_url(
    payload: MonitorUrlUpdate,
    url_monitor: VerifyURLMonitorOwnership,
    url_monitor_repo: Annotated[URLMonitorRepository, Depends(get_url_monitor_repo)],
):
    """Update a specific URL monitor entry by its ID."""

    url_monitor = await url_monitor_repo.update_url(
        url_id=url_monitor.id, url=payload.url
    )  # type: ignore

    logger.info(f"SUCCESS: Updated URL monitor entry with ID: {url_monitor.id}")
    return url_monitor


@router.delete("/{url_id}")
async def delete_monitor_url(
    url_monitor: VerifyURLMonitorOwnership,
    url_monitor_repo: Annotated[URLMonitorRepository, Depends(get_url_monitor_repo)],
):
    await url_monitor_repo.delete_url(url_monitor.id)
    return Response({}, status_code=status.HTTP_204_NO_CONTENT)
