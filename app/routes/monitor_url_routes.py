import logging
from uuid import UUID

from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException,
    status
)

from sqlalchemy.orm import Session

from app.config.database_config import get_db
from app.dependencies import CurrentUser, VerifyURLMonitorOwnership
from app.repositories.url_monitor_repository import URLMonitorRepository
from app.schemas.monitor_url_schemas import (
    MonitorUrlBase,
    MonitorUrlCreate, 
    MonitorUrlResponse, 
    MonitorUrlUpdate
)

router = APIRouter(prefix="/api/v1/monitors", tags=["Monitor URL"])
logger = logging.getLogger(__name__)
url_monitor_repo = URLMonitorRepository()

@router.post("/", response_model=MonitorUrlResponse, status_code=201)
async def create_monitor_url(payload: MonitorUrlCreate, current_user: CurrentUser):
    """Create a new URL monitor entry."""
    logger.info("INFO: Attempting to create a new URL monitor entry")
    
    new_url_monitor = await url_monitor_repo.add_url(payload.url, owner_id=current_user.id)
    logger.info(f"SUCCESS: Created new URL monitor entry with ID: {new_url_monitor.id}")
    return new_url_monitor


@router.get("/", response_model=list[MonitorUrlResponse])
async def get_all_monitor_urls(current_user: CurrentUser):
    """Retrieve all URL monitor entries."""
    logger.info("INFO: Attempting to reurn all URL monitor entries")
    
    url_monitors = await url_monitor_repo.get_all_urls(current_user.id)
    logger.info("SUCCESS: Returned all URL monitor entries")
    return url_monitors


@router.get("/{url_id}", response_model=MonitorUrlResponse)
async def get_monitor_url(url_monitor: VerifyURLMonitorOwnership):
    """Retrieve a specific URL monitor entry by its ID."""
    
    return url_monitor


@router.patch("/{url_id}", response_model=MonitorUrlResponse)
async def update_monitor_url(
    payload: MonitorUrlUpdate, 
    url_monitor: VerifyURLMonitorOwnership
):
    """Update a specific URL monitor entry by its ID."""
    
    url_monitor = await url_monitor_repo.update_url(
                    url_id=url_monitor.id, 
                    url=payload.url
                ) # type: ignore

    logger.info(f"SUCCESS: Updated URL monitor entry with ID: {url_monitor.id}")
    return url_monitor