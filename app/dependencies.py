import logging
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPBearer,
    OAuth2PasswordBearer,
)

from app.config.database_config import SessionLocal
from app.config.jwt_config import ALGORITHM
from app.config.settings import JWT_SECRET_KEY
from app.errors.environment_errors import EnvironmentVariableMissingError
from app.models.url_monitor import URLMonitor
from app.models.users import User
from app.repositories.url_monitor_repository import URLMonitorRepository
from app.repositories.user_repository import UserRepository
from app.services.error import BlacklistedTokenError
from app.services.redis_client import redis_client
from app.services.token_service import JWTTokenService

user_repo = UserRepository()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_db():
    async with SessionLocal() as session:
        yield session


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
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


async def verify_url_monitor_ownership(
    url_id: UUID, current_user: CurrentUser, url_repo: URLMonitorRepository = Depends()
):
    logger.info(f"INFO: Attempting to retrieve URL monitor entry with ID: {url_id}")

    url_monitor = await url_repo.get_url_by_id(url_id)
    if url_monitor is None:
        logger.exception(
            f"EXCEPTION: Could not find URL monitor entry with ID: {url_id}"
        )
        raise HTTPException(status_code=404, detail="URL monitor not found")

    if url_monitor.owner_id != current_user.id:
        logger.exception(
            f"SECURITY: User {current_user.id} tried to view User {url_monitor.owner_id} URL monitor {url_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized to view this URL Monitor",
        )

    logger.info(f"SUCCESS: Retrieved URL monitor entry with ID: {url_id}")
    return url_monitor


VerifyURLMonitorOwnership = Annotated[URLMonitor, Depends(verify_url_monitor_ownership)]
