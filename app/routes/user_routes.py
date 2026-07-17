from fastapi import APIRouter, HTTPException, status

from app.config.security_config import (
    dummy_hash_password, 
    hash_password, 
    verify_password
)
from app.repositories.url_monitor_repository import URLMonitorRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserCreate

router = APIRouter(prefix="/api/v1/users", tags=["User and Authentication"])

user_repo = UserRepository()

@router.post("/")
async def create_user_route(payload: UserCreate):
    username_exists = await user_repo.get_user_by_username(payload.username)
    email_exists = await user_repo.get_user_by_email(payload.email)
    
    if username_exists or email_exists:
        dummy_hash_password()
        
        raise HTTPException(
            detail="Account alread exists",
            status_code=status.HTTP_409_CONFLICT
        )
    
    hashed_password = hash_password(payload.password)
    return await user_repo.create_user(
                    username=payload.username,
                    email=payload.email,
                    hashed_password=hashed_password
                )