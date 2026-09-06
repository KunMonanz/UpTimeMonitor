from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.config.database_config import Base

if TYPE_CHECKING:
    from app.models.users import Group, User


class URLMonitor(Base):
    """Model for monitoring URLs."""

    __tablename__ = "url_monitor"
    __table_args__ = (
        CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_group_id IS NULL) OR "
            "(owner_user_id IS NULL AND owner_group_id IS NOT NULL)",
            name="ck_url_monitor_exactly_one_owner",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    is_up: Mapped[bool] = mapped_column(Boolean, default=False)
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_status_code: Mapped[int | None] = mapped_column(nullable=True)

    owner_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    owner_group_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("groups.id", ondelete="CASCADE"), nullable=True
    )

    owner_user: Mapped["User | None"] = relationship(
        back_populates="url_monitors",
        lazy="selectin",
        foreign_keys=[owner_user_id],
    )
    owner_group: Mapped["Group | None"] = relationship(
        back_populates="monitors",
        lazy="selectin",
        foreign_keys=[owner_group_id],
    )
