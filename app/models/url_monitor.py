from uuid import UUID
from uuid6 import uuid7

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, Uuid

from app.config.database_config import Base


class URLMonitor(Base):
    """Model for monitoring URLs."""
    __tablename__ = "url_monitor"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, default=False)