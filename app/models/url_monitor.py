from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.config.database_config import Base
from app.models.users import User


class URLMonitor(Base):
    """Model for monitoring URLs."""

    __tablename__ = "url_monitor"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    is_up: Mapped[bool] = mapped_column(Boolean, default=False)
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_status_code: Mapped[int | None] = mapped_column(nullable=True)

    owner: Mapped["User"] = relationship(back_populates="url_monitors")
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
