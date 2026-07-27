from typing import Generator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, DeclarativeBase, sessionmaker

from app.config.settings import DATABASE_URL

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment variables.")

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(
    bind=engine, 
    autocommit=False, 
    autoflush=False, 
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass


