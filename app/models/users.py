from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database_config import Base
from app.models.url_monitor import URLMonitor


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    
    url_monitors: Mapped[list["URLMonitor"]] = relationship(
        back_populates="owner", 
        cascade="all, delete-orphan"
    )
    
    