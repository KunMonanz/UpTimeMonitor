from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.config.database_config import Base

if TYPE_CHECKING:
    from app.models.url_monitor import URLMonitor


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    url_monitors: Mapped[list["URLMonitor"]] = relationship(  # type: ignore
        back_populates="owner", cascade="all, delete-orphan", lazy="selectin"
    )
