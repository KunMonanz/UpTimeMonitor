from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import UUID

from pydantic import HttpUrl
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors.url_monitor_errors import URLMonitorDoesNotExist
from app.models.url_monitor import URLMonitor
from app.models.users import Group, group_admins, user_groups


class URLMonitorRepository:
    """Repository for URLMonitor model."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _monitor_loader_options():
        return (
            selectinload(URLMonitor.owner_user),
            selectinload(URLMonitor.owner_group).selectinload(Group.members),
            selectinload(URLMonitor.owner_group).selectinload(Group.admins),
        )

    async def add_user_owned_url(self, url: HttpUrl, user_id: UUID) -> URLMonitor:
        name = urlparse(str(url)).netloc
        url_monitor = URLMonitor(url=str(url), owner_user_id=user_id, name=name)
        self.db.add(url_monitor)
        await self.db.commit()
        await self.db.refresh(url_monitor)
        return url_monitor

    async def add_group_owned_url(self, url: HttpUrl, group_id: UUID) -> URLMonitor:
        name = urlparse(str(url)).netloc
        url_monitor = URLMonitor(url=str(url), owner_group_id=group_id, name=name)
        self.db.add(url_monitor)
        await self.db.commit()
        await self.db.refresh(url_monitor)
        return url_monitor

    async def get_all_accessible_urls(self, user_id: UUID):
        member_group_ids = select(user_groups.c.group_id).where(
            user_groups.c.user_id == user_id
        )
        admin_group_ids = select(group_admins.c.group_id).where(
            group_admins.c.user_id == user_id
        )
        query = (
            select(URLMonitor)
            .where(
                or_(
                    URLMonitor.owner_user_id == user_id,
                    URLMonitor.owner_group_id.in_(member_group_ids),
                    URLMonitor.owner_group_id.in_(admin_group_ids),
                )
            )
            .options(*self._monitor_loader_options())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_all_urls(self):
        query = select(URLMonitor).options(*self._monitor_loader_options())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_url_by_id(self, url_id: UUID):
        query = (
            select(URLMonitor)
            .where(URLMonitor.id == url_id)
            .options(*self._monitor_loader_options())
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_url_status(
        self, monitor_id: UUID, is_up: bool, status_code: int | None
    ) -> bool:
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
            url_monitor.name = urlparse(str(url)).netloc
            await self.db.commit()
            await self.db.refresh(url_monitor)
            return url_monitor
        return None

    async def delete_url(self, url_id: UUID):
        url_monitor = await self.get_url_by_id(url_id)
        if url_monitor:
            await self.db.delete(url_monitor)
            await self.db.commit()
            return True
        return False
