from uuid import UUID

from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.url_monitor import URLMonitor
from app.config.database_config import SessionLocal


class URLMonitorRepository:
    """Repository for URLMonitor model."""

    def __init__(self):
        self.db = SessionLocal()

    async def add_url(self, url: HttpUrl, owner_id: UUID) -> URLMonitor:
        """Add a new URLMonitor entry to the database."""
        url_monitor = URLMonitor(url=str(url), owner_id=owner_id)
        self.db.add(url_monitor)
        await self.db.commit()
        await self.db.refresh(url_monitor)
        return url_monitor

    async def get_all_urls(self, user_id: UUID):
        """Retrieve all URLMonitor entries from the database."""
        query = select(URLMonitor)\
            .where(URLMonitor.owner_id == user_id)\
                .options(selectinload(URLMonitor.owner))
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_url_by_id(self, url_id: UUID):
        """Retrieve a specific URLMonitor entry by its ID."""
        query = select(URLMonitor).where(URLMonitor.id == url_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_url_status(self, url_id: UUID, status: bool):
        """Update the status of a specific URLMonitor entry."""
        url_monitor = await self.get_url_by_id(url_id)
        if url_monitor:
            url_monitor.status = status
            await self.db.commit()
            await self.db.refresh(url_monitor)
            return url_monitor
        return None

    async def update_url(self, url_id: UUID, url: HttpUrl):
        url_monitor = await self.get_url_by_id(url_id)
        if url_monitor:
            url_monitor.url = str(url)
            await self.db.commit()
            await self.db.refresh(url_monitor)
            return url_monitor
        return None
    
    async def delete_url(self, url_id: UUID):
        """Delete a specific URLMonitor entry by its ID."""
        url_monitor = await self.get_url_by_id(url_id)
        if url_monitor:
            await self.db.delete(url_monitor)
            await self.db.commit()
            return True
        return False