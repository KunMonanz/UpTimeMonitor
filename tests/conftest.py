import asyncio
import os
import sys
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_bootstrap.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-32-plus-bytes")
os.environ.setdefault("BACKEND_URL", "testserver.local")
os.environ.setdefault("FRONTEND_URL", "http://testserver.local")
os.environ.setdefault("EMAIL_ENGINE", "smtp")
os.environ.setdefault("MAIL_USERNAME", "test@example.com")
os.environ.setdefault("MAIL_PASSWORD", "password")
os.environ.setdefault("MAIL_SERVER", "smtp.example.com")

import app.config.limiter as limiter_module
import app.dependencies as dependencies_module
from app.config.database_config import Base
from app.config.jwt_config import ALGORITHM
from app.config.security_config import hash_password
from app.dependencies import get_db
from app.models.url_monitor import URLMonitor
from app.models.users import Group, User
from app.routes import cache_keys as cache_keys_module
from app.routes import group_routes, monitor_url_routes, user_routes
from app.services import token_service as token_service_module
from app.utils import email_utils
from main import app


def run_async(coro):
    return asyncio.run(coro)


class FakeRedis:
    def __init__(self):
        self._store: dict[str, Any] = {}
        self._ttl: dict[str, int | None] = {}

    async def set(self, key: str, value: Any, ex: int | None = None, nx: bool = False):
        if nx and key in self._store:
            return False
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        self._store[key] = value
        self._ttl[key] = ex
        return True

    async def get(self, key: str):
        return self._store.get(key)

    async def delete(self, *keys: str):
        deleted = 0
        for key in keys:
            if key in self._store:
                deleted += 1
                self._store.pop(key, None)
                self._ttl.pop(key, None)
        return deleted

    async def ttl(self, key: str):
        if key not in self._store:
            return -2
        ttl = self._ttl.get(key)
        return -1 if ttl is None else ttl

    async def keys(self, pattern: str):
        return [key for key in self._store if fnmatch(key, pattern)]


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    fake = FakeRedis()

    class _TokenService:
        def __init__(self, redis=None, prefix: str = "verify_token"):
            self._inner = token_service_module.TokenService(
                redis=cast(Any, fake), prefix=prefix
            )

        async def generate_token(self, identifier: str, ttl: int):
            return await self._inner.generate_token(identifier=identifier, ttl=ttl)

        async def verify_token(self, token: str, consume: bool = True):
            return await self._inner.verify_token(token=token, consume=consume)

    class _JWTTokenService:
        def __init__(self, redis=None, prefix: str = "jwt"):
            self._inner = token_service_module.JWTTokenService(
                redis=cast(Any, fake), prefix=prefix
            )

        async def blacklist(self, token, identifier, ttl=15 * 60):
            return await self._inner.blacklist(
                token=token, identifier=identifier, ttl=ttl
            )

        async def verify_jwt(self, token):
            return await self._inner.verify_jwt(token)

    monkeypatch.setattr(user_routes, "redis_client", fake)
    monkeypatch.setattr(group_routes, "redis_client", fake)
    monkeypatch.setattr(monitor_url_routes, "redis_client", fake)
    monkeypatch.setattr(cache_keys_module, "redis_client", fake)
    monkeypatch.setattr(limiter_module, "redis_client", fake)
    monkeypatch.setattr(dependencies_module, "redis_client", fake)
    monkeypatch.setattr(user_routes, "TokenService", _TokenService)
    monkeypatch.setattr(group_routes, "TokenService", _TokenService)
    monkeypatch.setattr(dependencies_module, "JWTTokenService", _JWTTokenService)
    monkeypatch.setattr(app.state.limiter, "enabled", False, raising=False)

    return fake


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    emails: list[dict[str, Any]] = []

    def fake_delay(**kwargs):
        emails.append(kwargs)

    monkeypatch.setattr(email_utils.send_async_email_task, "delay", fake_delay)
    return emails


@pytest.fixture
def session_factory(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    testing_session_factory = async_sessionmaker(
        bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
    )

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    run_async(_setup())
    yield testing_session_factory
    run_async(engine.dispose())


@pytest.fixture
def client(
    session_factory, fake_redis, sent_emails
) -> Generator[TestClient, None, None]:
    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    def _auth_headers(user: User) -> dict[str, str]:
        token = jwt.encode(
            {
                "sub": user.username,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            },
            os.environ["JWT_SECRET_KEY"],
            algorithm=ALGORITHM,
        )
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers


@pytest.fixture
def create_user(session_factory):
    def _create_user(
        username: str,
        email: str,
        password: str = "Password123!",
        verified: bool = True,
    ) -> User:
        async def _inner():
            async with session_factory() as session:
                user = User(
                    username=username,
                    email=email,
                    hashed_password=await hash_password(password),
                    is_email_verified=verified,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                return user

        return run_async(_inner())

    return _create_user


@pytest.fixture
def create_group(session_factory):
    def _create_group(
        name: str,
        admin_user_id: UUID,
        description: str | None = None,
        member_user_ids: list[UUID] | None = None,
        admin_user_ids: list[UUID] | None = None,
    ) -> Group:
        member_user_ids = member_user_ids or []
        admin_user_ids = admin_user_ids or []

        async def _inner():
            async with session_factory() as session:
                group = Group(name=name, description=description)

                all_member_ids = {admin_user_id, *member_user_ids, *admin_user_ids}
                for user_id in all_member_ids:
                    user = await session.get(User, user_id)
                    assert user is not None
                    group.members.append(user)

                admin_ids = {admin_user_id, *admin_user_ids}
                for user_id in admin_ids:
                    user = await session.get(User, user_id)
                    assert user is not None
                    group.admins.append(user)

                session.add(group)
                await session.commit()
                await session.refresh(group)
                return group

        return run_async(_inner())

    return _create_group


@pytest.fixture
def create_monitor(session_factory):
    def _create_monitor(
        url: str,
        owner_user_id: UUID | None = None,
        owner_group_id: UUID | None = None,
        is_up: bool = False,
    ) -> URLMonitor:
        async def _inner():
            async with session_factory() as session:
                monitor = URLMonitor(
                    name=url.split("//", 1)[-1],
                    url=url,
                    owner_user_id=owner_user_id,
                    owner_group_id=owner_group_id,
                    is_up=is_up,
                )
                session.add(monitor)
                await session.commit()
                await session.refresh(monitor)
                return monitor

        return run_async(_inner())

    return _create_monitor


@pytest.fixture
def get_user(session_factory):
    def _get_user(user_id: UUID) -> User:
        async def _inner():
            async with session_factory() as session:
                user = await session.get(User, user_id)
                assert user is not None
                return user

        return run_async(_inner())

    return _get_user


@pytest.fixture
def get_group(session_factory):
    def _get_group(group_id: UUID) -> Group | None:
        async def _inner():
            async with session_factory() as session:
                return await session.get(Group, group_id)

        return run_async(_inner())

    return _get_group


@pytest.fixture
def get_monitor(session_factory):
    def _get_monitor(monitor_id: UUID) -> URLMonitor | None:
        async def _inner():
            async with session_factory() as session:
                return await session.get(URLMonitor, monitor_id)

        return run_async(_inner())

    return _get_monitor
