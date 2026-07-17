import logging
from uuid import UUID

from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException
)

from sqlalchemy.orm import Session

from app.config.database_config import get_db
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
async def create_monitor_url(payload: MonitorUrlCreate):
    """Create a new URL monitor entry."""
    logger.info("INFO: Attempting to create a new URL monitor entry")
    
    new_url_monitor = await url_monitor_repo.add_url(payload.url)
    logger.info(f"SUCCESS: Created new URL monitor entry with ID: {new_url_monitor.id}")
    return new_url_monitor

@router.get("/", response_model=list[MonitorUrlResponse])
async def get_all_monitor_urls():
    """Retrieve all URL monitor entries."""
    logger.info("INFO: Attempting to reurn all URL monitor entries")
    
    url_monitors = await url_monitor_repo.get_all_urls()
    logger.info("SUCCESS: Returned all URL monitor entries")
    return url_monitors

@router.get("/{url_id}", response_model=MonitorUrlResponse)
async def get_monitor_url(url_id: UUID):
    """Retrieve a specific URL monitor entry by its ID."""
    logger.info(f"INFO: Attempting to retrieve URL monitor entry with ID: {url_id}")
    
    url_monitor = await url_monitor_repo.get_url_by_id(url_id)
    if not url_monitor:
        logger.exception(f"EXCEPTION: Could not find URL monitor entry with ID: {url_id}")
        raise HTTPException(status_code=404, detail="URL monitor not found")
    
    logger.info(f"SUCCESS: Retrieved URL monitor entry with ID: {url_id}")
    return url_monitor

@router.patch("/{url_id}", response_model=MonitorUrlResponse)
async def update_monitor_url(url_id: UUID, payload: MonitorUrlBase):
    """Update a specific URL monitor entry by its ID."""
    logger.info(f"INFO: Attempting to update URL monitor entry with ID: {url_id}")
    
    url_monitor_exists = await url_monitor_repo.update_url(
                                url_id=url_id, 
                                url=payload.url
                            )
    if not url_monitor_exists:
        logger.exception(f"EXCEPTION: Could not find URL monitor entry with ID: {url_id}")
        raise HTTPException(status_code=404, detail="URL monitor not found")
    
    logger.info(f"SUCCESS: Updated URL monitor entry with ID: {url_id}")
    return url_monitor_exists