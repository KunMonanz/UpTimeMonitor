import logging
from urllib.parse import urlparse
from uuid import UUID

from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors.group_errors import (
    GroupDoesNotExistError,
    MonitorNotInGroupError,
    UserAlreadyInGroupError,
    UserNotGroupAdminError,
    UserNotGroupMemberError,
)
from app.errors.url_monitor_errors import URLMonitorDoesNotExist
from app.errors.user_errors import UserDoesNotExist
from app.models.url_monitor import URLMonitor
from app.models.users import Group, User

logger = logging.getLogger(__name__)


class GroupRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_group(
        self, name: str, user_id: UUID, description: str | None = None
    ) -> Group:
        new_group = Group(name=name, description=description)

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise UserDoesNotExist("User not found")

        new_group.members.append(user)
        new_group.admins.append(user)

        self.db.add(new_group)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise
        await self.db.refresh(new_group)

        return new_group

    async def get_group_by_id(self, group_id: UUID, user_id: UUID) -> Group:
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user is None:
            raise UserDoesNotExist("User not found")

        if not any(group.id == group_id for group in user.groups):
            raise UserNotGroupMemberError("User is not a member of this group")

        result = await self.db.execute(
            select(Group)
            .where(Group.id == group_id)
            .options(selectinload(Group.members), selectinload(Group.admins))
        )
        try:
            return result.scalar_one()
        except NoResultFound:
            raise GroupDoesNotExistError("Group not found")

    async def get_group_by_id_no_user_check(self, group_id: UUID) -> Group:
        result = await self.db.execute(
            select(Group)
            .where(Group.id == group_id)
            .options(selectinload(Group.members), selectinload(Group.admins))
        )
        try:
            return result.scalar_one()
        except NoResultFound:
            raise GroupDoesNotExistError("Group not found")

    async def ensure_group_admin(self, group_id: UUID, admin_id: UUID) -> Group:
        group = await self.get_group_by_id_no_user_check(group_id)
        if not any(admin.id == admin_id for admin in group.admins):
            raise UserNotGroupAdminError(
                "User does not have permission to manage this group"
            )
        return group

    async def ensure_group_member(self, group_id: UUID, user_id: UUID) -> Group:
        group = await self.get_group_by_id_no_user_check(group_id)
        if not any(member.id == user_id for member in group.members):
            raise UserNotGroupMemberError(
                "User does not have permission to access this group"
            )
        return group

    async def add_user_to_group(
        self, group_id: UUID, new_member_id: UUID, admin_id: UUID
    ) -> None:
        group = await self.ensure_group_admin(group_id, admin_id)

        result = await self.db.execute(select(User).where(User.id == new_member_id))
        new_member = result.scalar_one_or_none()
        if new_member is None:
            raise UserDoesNotExist("User not found")

        if new_member in group.members:
            raise UserAlreadyInGroupError("User is already a member of this group")

        group.members.append(new_member)
        try:
            await self.db.commit()
        except IntegrityError:
            logger.error(
                f"IntegrityError while adding user {new_member_id} to group {group_id}"
            )
            await self.db.rollback()
            raise

    async def remove_user_from_group(
        self, group_id: UUID, member_id: UUID, admin_id: UUID
    ) -> None:
        group = await self.ensure_group_admin(group_id, admin_id)

        result = await self.db.execute(select(User).where(User.id == member_id))
        member = result.scalar_one_or_none()
        if member is None:
            raise UserDoesNotExist("User not found")

        if member not in group.members:
            raise UserNotGroupMemberError("User is not a member of this group")

        group.members.remove(member)

        if member in group.admins:
            group.admins.remove(member)

        try:
            await self.db.commit()
        except IntegrityError:
            logger.error(
                f"IntegrityError while removing user {member_id} from group {group_id}"
            )
            await self.db.rollback()
            raise

    async def create_new_monitor_for_group(
        self, group_id: UUID, url: HttpUrl, admin_id: UUID
    ) -> URLMonitor:
        group = await self.ensure_group_admin(group_id, admin_id=admin_id)
        name = urlparse(str(url)).netloc or urlparse(str(url)).path
        new_monitor = URLMonitor(name=name, url=url, owner_group_id=group.id)
        self.db.add(new_monitor)
        try:
            await self.db.commit()
        except IntegrityError:
            logger.error(f"IntegrityError while creating monitor for group {group_id}")
            await self.db.rollback()
            raise
        await self.db.refresh(new_monitor)
        return new_monitor

    async def delete_monitor_from_group(
        self, group_id: UUID, monitor_id: UUID, admin_id: UUID
    ) -> None:
        group = await self.ensure_group_admin(group_id, admin_id=admin_id)
        monitor_result = await self.db.execute(
            select(URLMonitor).where(URLMonitor.id == monitor_id)
        )
        monitor = monitor_result.scalar_one_or_none()
        if monitor is None:
            raise URLMonitorDoesNotExist("Monitor not found")
        if monitor.owner_group_id != group.id:
            raise MonitorNotInGroupError("Monitor does not belong to this group")

        await self.db.delete(monitor)
        try:
            await self.db.commit()
        except IntegrityError:
            logger.error(
                f"IntegrityError while deleting monitor {monitor_id} from group {group_id}"
            )
            await self.db.rollback()
            raise

    async def delete_group(self, group_id: UUID, admin_id: UUID) -> None:
        group = await self.ensure_group_admin(group_id, admin_id)
        await self.db.delete(group)
        try:
            await self.db.commit()
        except IntegrityError:
            logger.error(f"IntegrityError while deleting group {group_id}")
            await self.db.rollback()
            raise

    async def get_group_urls(self, group_id: UUID, user_id: UUID) -> list[URLMonitor]:
        group = await self.ensure_group_member(group_id, user_id)
        return group.monitors

    async def get_group_members(self, group_id: UUID, user_id: UUID) -> list[User]:
        group = await self.ensure_group_member(group_id, user_id)
        return group.members
