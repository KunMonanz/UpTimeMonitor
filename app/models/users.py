from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.config.database_config import Base

if TYPE_CHECKING:
    from app.models.url_monitor import URLMonitor


user_groups = Table(
    "user_groups",
    Base.metadata,
    Column(
        "user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "group_id", Uuid, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    ),
)


group_admins = Table(
    "group_admins",
    Base.metadata,
    Column(
        "user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "group_id", Uuid, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    ),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    groups: Mapped[list["Group"]] = relationship(
        secondary=user_groups, back_populates="members", lazy="selectin"
    )
    admin_groups: Mapped[list["Group"]] = relationship(
        secondary=group_admins, back_populates="admins", lazy="selectin"
    )
    url_monitors: Mapped[list["URLMonitor"]] = relationship(
        back_populates="owner_user",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="URLMonitor.owner_user_id",
    )


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    admins: Mapped[list["User"]] = relationship(
        secondary=group_admins, back_populates="admin_groups", lazy="selectin"
    )
    members: Mapped[list["User"]] = relationship(
        secondary=user_groups, back_populates="groups", lazy="selectin"
    )
    monitors: Mapped[list["URLMonitor"]] = relationship(
        back_populates="owner_group",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="URLMonitor.owner_group_id",
    )
