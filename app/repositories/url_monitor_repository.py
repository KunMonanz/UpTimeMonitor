from datetime import datetime, timezone
from uuid import UUID

from pydantic import HttpUrl
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors.url_monitor_errors import (
    DuplicateURLMonitorForOwner,
    URLMonitorDoesNotExist,
)
from app.models.url_monitor import URLMonitor
from app.models.users import Group, group_admins, user_groups
from app.utils.monitor_url_utils import get_monitor_name, normalize_monitor_url


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

    async def get_existing_owner_monitor(
        self,
        normalized_url: str,
        owner_user_id: UUID | None = None,
        owner_group_id: UUID | None = None,
        exclude_monitor_id: UUID | None = None,
    ) -> URLMonitor | None:
        query = select(URLMonitor)

        if owner_user_id is not None:
            query = query.where(URLMonitor.owner_user_id == owner_user_id)
        elif owner_group_id is not None:
            query = query.where(URLMonitor.owner_group_id == owner_group_id)
        else:
            raise ValueError("An owner_user_id or owner_group_id is required")

        if exclude_monitor_id is not None:
            query = query.where(URLMonitor.id != exclude_monitor_id)

        result = await self.db.execute(query)
        monitors = result.scalars().all()

        for monitor in monitors:
            if normalize_monitor_url(monitor.url) == normalized_url:
                return monitor

        return None

    async def ensure_owner_monitor_is_unique(
        self,
        normalized_url: str,
        owner_user_id: UUID | None = None,
        owner_group_id: UUID | None = None,
        exclude_monitor_id: UUID | None = None,
    ) -> None:
        existing_monitor = await self.get_existing_owner_monitor(
            normalized_url=normalized_url,
            owner_user_id=owner_user_id,
            owner_group_id=owner_group_id,
            exclude_monitor_id=exclude_monitor_id,
        )
        if existing_monitor is not None:
            raise DuplicateURLMonitorForOwner()

    async def add_user_owned_url(self, url: HttpUrl, user_id: UUID) -> URLMonitor:
        normalized_url = normalize_monitor_url(str(url))
        await self.ensure_owner_monitor_is_unique(
            normalized_url=normalized_url,
            owner_user_id=user_id,
        )
        url_monitor = URLMonitor(
            url=normalized_url,
            owner_user_id=user_id,
            name=get_monitor_name(normalized_url),
        )
        self.db.add(url_monitor)
        await self.db.commit()
        await self.db.refresh(url_monitor)
        return url_monitor

    async def add_group_owned_url(self, url: HttpUrl, group_id: UUID) -> URLMonitor:
        normalized_url = normalize_monitor_url(str(url))
        await self.ensure_owner_monitor_is_unique(
            normalized_url=normalized_url,
            owner_group_id=group_id,
        )
        url_monitor = URLMonitor(
            url=normalized_url,
            owner_group_id=group_id,
            name=get_monitor_name(normalized_url),
        )
        self.db.add(url_monitor)
        await self.db.commit()
        await self.db.refresh(url_monitor)
        return url_monitor

    async def get_all_accessible_urls(
        self, user_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[URLMonitor], int]:
        member_group_ids = select(user_groups.c.group_id).where(
            user_groups.c.user_id == user_id
        )
        admin_group_ids = select(group_admins.c.group_id).where(
            group_admins.c.user_id == user_id
        )
        filter_clause = or_(
            URLMonitor.owner_user_id == user_id,
            URLMonitor.owner_group_id.in_(member_group_ids),
            URLMonitor.owner_group_id.in_(admin_group_ids),
        )

        count_query = select(func.count()).select_from(URLMonitor).where(filter_clause)
        total = await self.db.scalar(count_query)

        query = (
            select(URLMonitor)
            .where(filter_clause)
            .order_by(URLMonitor.id.desc())
            .offset(offset)
            .limit(limit)
            .options(*self._monitor_loader_options())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def get_all_urls(self):
        query = (
            select(URLMonitor)
            .order_by(URLMonitor.id.desc())
            .options(*self._monitor_loader_options())
        )
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

    def apply_url_status_update(
        self, monitor: URLMonitor, is_up: bool, status_code: int | None
    ) -> bool:
        was_up = monitor.is_up
        monitor.is_up = is_up
        monitor.last_checked_at = datetime.now(timezone.utc)
        monitor.last_status_code = status_code
        monitor.consecutive_failures = 0 if is_up else monitor.consecutive_failures + 1
        return was_up != is_up

    async def save_url_status_updates(self) -> None:
        await self.db.commit()

    async def update_url_status(
        self, monitor_id: UUID, is_up: bool, status_code: int | None
    ) -> bool:
        monitor = await self.get_url_by_id(monitor_id)
        if monitor:
            status_changed = self.apply_url_status_update(monitor, is_up, status_code)
            await self.save_url_status_updates()
            await self.db.refresh(monitor)
            return status_changed
        raise URLMonitorDoesNotExist("Url not found")

    async def update_url(self, url_id: UUID, url: HttpUrl):
        url_monitor = await self.get_url_by_id(url_id)
        if url_monitor:
            normalized_url = normalize_monitor_url(str(url))
            await self.ensure_owner_monitor_is_unique(
                normalized_url=normalized_url,
                owner_user_id=url_monitor.owner_user_id,
                owner_group_id=url_monitor.owner_group_id,
                exclude_monitor_id=url_monitor.id,
            )
            url_monitor.url = normalized_url
            url_monitor.name = get_monitor_name(normalized_url)
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
