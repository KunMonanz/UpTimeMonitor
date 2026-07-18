from uuid import UUID
from pydantic import EmailStr

from fastapi import APIRouter, HTTPException, status

from app.config.jwt_config import CurrentUser, create_access_token
from app.config.security_config import (
    dummy_hash_password, 
    hash_password, 
    verify_password
)
from app.repositories.url_monitor_repository import URLMonitorRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import (
    Token, 
    UserCreate, 
    UserLogin, 
    UserResponse
)
from app.utils.email_utils import is_email

router = APIRouter(prefix="/api/v1/users", tags=["User and Authentication"])

user_repo = UserRepository()

@router.post("/", response_model=UserResponse)
async def create_user_route(payload: UserCreate):
    username_exists = await user_repo.get_user_by_username(payload.username)
    email_exists = await user_repo.get_user_by_email(payload.email)
    
    if username_exists or email_exists:
        await dummy_hash_password()
        
        raise HTTPException(
            detail="Account alread exists",
            status_code=status.HTTP_409_CONFLICT
        )
    
    hashed_password = str(await hash_password(payload.password))
    return await user_repo.create_user(
                    username=payload.username,
                    email=payload.email,
                    hashed_password=hashed_password
                )

@router.post("/login", response_model=Token)
async def login_for_access_token(
    payload: UserLogin
):
    if await is_email(payload.username_or_email):
        user = await user_repo.get_user_by_email(payload.username_or_email)
    else:
        user = await user_repo.get_user_by_username(payload.username_or_email)
    if user is None:
        await dummy_hash_password()
        raise HTTPException(
            detail="Account does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )
    is_correct_password = await verify_password(payload.password, user.hashed_password)
    if is_correct_password:
        access_token = await create_access_token({"sub": user.username})
        return Token(access_token=access_token, token_type="bearer")
            

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id_route(user_id: UUID, current_user: CurrentUser):
    user = await user_repo.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            detail="User not found",
            status_code=status.HTTP_404_NOT_FOUND
        )
    return user

@router.get("/{username}", response_model=UserResponse)
async def get_user_by_username_route(username: str, current_user: CurrentUser):
    user = await user_repo.get_user_by_username(username)
    if user is None:
        raise HTTPException(
            detail="User not found",
            status_code=status.HTTP_404_NOT_FOUND
        )
    return user

