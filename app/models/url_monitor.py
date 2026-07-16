from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean

from app.config.database_config import Base


class URLMonitor(Base):
    """Model for monitoring URLs."""
    __tablename__ = "url_monitor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, default=False)