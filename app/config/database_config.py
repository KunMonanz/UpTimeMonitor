from typing import Generator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config.settings import DATABASE_URL
from app.errors.environment_errors import EnvironmentVariableMissingError

if not DATABASE_URL:
    raise EnvironmentVariableMissingError("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True)
SessionLocal = async_sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass
