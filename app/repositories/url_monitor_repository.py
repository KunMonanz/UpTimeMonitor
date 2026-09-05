from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import UUID

from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.database_config import SessionLocal
from app.errors.url_monitor_errors import URLMonitorDoesNotExist
from app.models.url_monitor import URLMonitor


class URLMonitorRepository:
    """Repository for URLMonitor model."""

    def __init__(self, db: AsyncSession):
        self.db = SessionLocal()

    async def add_url(self, url: HttpUrl, owner_id: UUID) -> URLMonitor:
        """Add a new URLMonitor entry to the database."""
        name = urlparse(str(url)).netloc
        url_monitor = URLMonitor(url=str(url), owner_id=owner_id, name=name)
        self.db.add(url_monitor)
        await self.db.commit()
        await self.db.refresh(url_monitor)
        return url_monitor

    async def get_all_user_urls(self, user_id: UUID):
        """Retrieve all URLMonitor entries from the database."""
        query = (
            select(URLMonitor)
            .where(URLMonitor.owner_id == user_id)
            .options(selectinload(URLMonitor.owner))
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_all_urls(self):
        query = select(URLMonitor).options(selectinload(URLMonitor.owner))
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_url_by_id(self, url_id: UUID):
        """Retrieve a specific URLMonitor entry by its ID."""
        query = (
            select(URLMonitor)
            .where(URLMonitor.id == url_id)
            .options(selectinload(URLMonitor.owner))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_url_status(
        self, monitor_id: UUID, is_up: bool, status_code: int | None
    ) -> bool:
        """Returns True if this check represents a state transition worth alerting on."""
        monitor = await self.get_url_by_id(monitor_id)
        if monitor:
            was_up = monitor.is_up

            monitor.is_up = is_up
            monitor.last_checked_at = datetime.now(timezone.utc)
            monitor.last_status_code = status_code
            monitor.consecutive_failures = (
                0 if is_up else monitor.consecutive_failures + 1
            )

            await self.db.commit()
            await self.db.refresh(monitor)

            return was_up != is_up
        raise URLMonitorDoesNotExist("Url not found")

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
