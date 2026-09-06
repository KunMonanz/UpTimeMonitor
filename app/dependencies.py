import logging
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database_config import SessionLocal
from app.config.jwt_config import ALGORITHM
from app.config.settings import JWT_SECRET_KEY
from app.errors.environment_errors import EnvironmentVariableMissingError
from app.models.url_monitor import URLMonitor
from app.models.users import User
from app.repositories.group_repository import GroupRepository
from app.repositories.url_monitor_repository import URLMonitorRepository
from app.repositories.user_repository import UserRepository
from app.services.error import BlacklistedTokenError
from app.services.redis_client import redis_client
from app.services.token_service import JWTTokenService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_db():
    async with SessionLocal() as session:
        yield session


def get_url_monitor_repo(db: AsyncSession = Depends(get_db)) -> URLMonitorRepository:
    return URLMonitorRepository(db)


def get_group_repo(db: AsyncSession = Depends(get_db)) -> GroupRepository:
    return GroupRepository(db)


def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
):
    credential_exception = HTTPException(
        detail="Could not validate credentials",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )

    if not JWT_SECRET_KEY:
        raise EnvironmentVariableMissingError("JWT_SECRET_KEY")

    if not ALGORITHM:
        raise EnvironmentVariableMissingError("ALGORITHM")
    jwt_service = JWTTokenService(redis=redis_client)

    try:
        await jwt_service.verify_jwt(token)
    except BlacklistedTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is blacklisted",
        )

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credential_exception
    except jwt.InvalidTokenError:
        raise credential_exception
    user = await user_repo.get_user_by_username(username=username)
    if user is None:
        raise credential_exception
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def verify_url_monitor_access(
    url_id: UUID,
    current_user: CurrentUser,
    url_repo: Annotated[URLMonitorRepository, Depends(get_url_monitor_repo)],
):
    logger.info(f"INFO: Attempting to retrieve URL monitor entry with ID: {url_id}")

    url_monitor = await url_repo.get_url_by_id(url_id)
    if url_monitor is None:
        logger.exception(
            f"EXCEPTION: Could not find URL monitor entry with ID: {url_id}"
        )
        raise HTTPException(status_code=404, detail="URL monitor not found")

    if url_monitor.owner_user_id == current_user.id:
        logger.info(
            f"SUCCESS: Retrieved user-owned URL monitor entry with ID: {url_id}"
        )
        return url_monitor

    if url_monitor.owner_group is not None and (
        any(member.id == current_user.id for member in url_monitor.owner_group.members)
        or any(admin.id == current_user.id for admin in url_monitor.owner_group.admins)
    ):
        logger.info(
            f"SUCCESS: Retrieved group-owned URL monitor entry with ID: {url_id}"
        )
        return url_monitor

    logger.exception(
        f"SECURITY: User {current_user.id} tried to access URL monitor {url_id} without permission"
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized to access this URL Monitor",
    )


async def verify_url_monitor_management(
    url_id: UUID,
    current_user: CurrentUser,
    url_repo: Annotated[URLMonitorRepository, Depends(get_url_monitor_repo)],
):
    url_monitor = await verify_url_monitor_access(url_id, current_user, url_repo)

    if url_monitor.owner_user_id == current_user.id:
        return url_monitor

    if url_monitor.owner_group is not None and any(
        admin.id == current_user.id for admin in url_monitor.owner_group.admins
    ):
        return url_monitor

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only group admins can modify this URL Monitor",
    )


AccessibleURLMonitor = Annotated[URLMonitor, Depends(verify_url_monitor_access)]
ManageableURLMonitor = Annotated[URLMonitor, Depends(verify_url_monitor_management)]
