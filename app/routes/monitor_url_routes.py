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
from app.config.jwt_config import CurrentUser
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
    
    new_url_monitor = await url_monitor_repo.add_url(payload.url)
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
async def get_monitor_url(url_id: UUID, current_user: CurrentUser):
    """Retrieve a specific URL monitor entry by its ID."""
    logger.info(f"INFO: Attempting to retrieve URL monitor entry with ID: {url_id}")
    
    url_monitor = await url_monitor_repo.get_url_by_id(url_id)

    if url_monitor is None:
        logger.exception(f"EXCEPTION: Could not find URL monitor entry with ID: {url_id}")
        raise HTTPException(status_code=404, detail="URL monitor not found")
    
    if url_monitor.owner_id != current_user.id:
        logger.exception(f"SECURITY: User {current_user.id} tried to view User {url_monitor.owner_id} URL monitor {url_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized to view this URL Monitor"
        )
        
    logger.info(f"SUCCESS: Retrieved URL monitor entry with ID: {url_id}")
    return url_monitor


@router.patch("/{url_id}", response_model=MonitorUrlResponse)
async def update_monitor_url(url_id: UUID, payload: MonitorUrlBase, current_user: CurrentUser):
    """Update a specific URL monitor entry by its ID."""
    logger.info(f"INFO: Attempting to update URL monitor entry with ID: {url_id}")
    
    url_monitor = await url_monitor_repo.get_url_by_id(url_id=url_id)
    if not url_monitor:
        logger.exception(f"EXCEPTION: Could not find URL monitor entry with ID: {url_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="URL monitor not found"
        )
    if url_monitor.owner_id != current_user.id:
        logger.exception(f"SECURITY: User {current_user.id} tried to edit User {url_monitor.owner_id} URL monitor {url_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized to edit this URL Monitor"
        )
    await url_monitor_repo.update_url(
        url_id=url_monitor.id, 
        url=payload.url
    )

    logger.info(f"SUCCESS: Updated URL monitor entry with ID: {url_id}")
    return url_monitor