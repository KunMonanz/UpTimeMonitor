from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt

from app.config.settings import JWT_SECRET_KEY
from app.errors.environment_errors import EnvironmentVariableMissingError
from app.models.users import User
from app.repositories.user_repository import UserRepository

ALGORITHM = "HS256"


async def create_access_token(payload: dict, expires_delta: timedelta | None = None):
    data = payload.copy()
    if not JWT_SECRET_KEY:
        raise EnvironmentVariableMissingError("JWT_SECRET_KEY")
    if expires_delta:
        exp = datetime.now(timezone.utc) + expires_delta
    else:
        exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    data.update({"exp": exp})
    return jwt.encode(data, JWT_SECRET_KEY, algorithm=ALGORITHM)
