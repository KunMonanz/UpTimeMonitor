from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.config.database_config import get_db
from app.repositories.url_monitor_repository import URLMonitorRepository
from app.schemas.monitor_url_schemas import (
    MonitorUrlCreate, 
    MonitorUrlResponse, 
    MonitorUrlUpdate
)

router = APIRouter(prefix="/api/v1/monitors", tags=["Monitor URL"])

url_monitor_repo = URLMonitorRepository()

@router.post("/", response_model=MonitorUrlResponse, status_code=201)
async def create_monitor_url(payload: MonitorUrlCreate):
    """Create a new URL monitor entry."""
    new_url_monitor = await url_monitor_repo.add_url(payload.url)
    return new_url_monitor


@router.get("/", response_model=list[MonitorUrlResponse])
async def get_all_monitor_urls():
    """Retrieve all URL monitor entries."""
    return await url_monitor_repo.get_all_urls()