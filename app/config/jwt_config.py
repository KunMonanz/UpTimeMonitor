import jwt
from typing import Annotated
from datetime import timedelta, datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config.settings import JWT_SECRET_KEY
from app.models.users import User
from app.repositories.user_repository import UserRepository

ALGORITHM="HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
user_repo = UserRepository()

async def create_access_token(payload: dict, expires_delta: timedelta | None =None):
    data = payload.copy()
    if not JWT_SECRET_KEY:
        raise Exception("ERROR: JWT_SECRET_KEY is missing")
    if expires_delta:
        exp = datetime.now(timezone.utc) + expires_delta
    else:
        exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    data.update({"exp": exp})
    return jwt.encode(data, JWT_SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credential_exception = HTTPException(
        detail="Could not validate credentials",
        status_code=status.HTTP_401_UNAUTHORIZED
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