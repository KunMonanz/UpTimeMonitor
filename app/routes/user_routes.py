from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import EmailStr

from app.config.security_config import (
    dummy_hash_password, 
    hash_password, 
    verify_password
)
from app.repositories.url_monitor_repository import URLMonitorRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserCreate, UserResponse

router = APIRouter(prefix="/api/v1/users", tags=["User and Authentication"])

user_repo = UserRepository()

@router.post("/", response_model=UserResponse)
async def create_user_route(payload: UserCreate):
    username_exists = await user_repo.get_user_by_username(payload.username)
    email_exists = await user_repo.get_user_by_email(payload.email)
    
    if username_exists or email_exists:
        dummy_hash_password()
        
        raise HTTPException(
            detail="Account alread exists",
            status_code=status.HTTP_409_CONFLICT
        )
    
    hashed_password = str(hash_password(payload.password))
    return await user_repo.create_user(
                    username=payload.username,
                    email=payload.email,
                    hashed_password=hashed_password
                )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id_route(user_id: UUID):
    user_exists = await user_repo.get_user_by_id(user_id)
    if not user_exists:
        raise HTTPException(
            detail="User not found",
            status_code=status.HTTP_404_NOT_FOUND
        )
    return user_exists

@router.get("/{username}", response_model=UserResponse)
async def get_user_by_username_route(username: str):
    user_exists = await user_repo.get_user_by_username(username)
    if not user_exists:
        raise HTTPException(
            detail="User not found",
            status_code=status.HTTP_404_NOT_FOUND
        )
    return user_exists

