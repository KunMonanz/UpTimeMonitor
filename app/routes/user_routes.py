from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.config.jwt_config import create_access_token
from app.config.security_config import (
    dummy_hash_password, 
    hash_password, 
    verify_password
)
from app.dependencies import CurrentUser, get_db
from app.repositories.user_repository import UserRepository
from app.repositories.error import UserDoesNotExist
from app.schemas.user_schema import (
    Token, 
    UserCreate, 
    UserLogin, 
    UserResponse,
    UserUsernameUpdate
)
from app.services.token_service import TokenService
from app.utils.email_utils import is_email, send_verification
from app.config.limiter import limiter

router = APIRouter(prefix="/api/v1/users", tags=["User and Authentication"])

user_repo = UserRepository()


@router.post("/", response_model=UserResponse)
@limiter.limit("3/hour")
async def create_user_route(request: Request, payload: UserCreate):
    try:
        await user_repo.get_user_by_username(payload.username)
        username_exists = True
    except UserDoesNotExist:
        username_exists = False

    try:
        await user_repo.get_user_by_email(payload.email)
        email_exists = True
    except UserDoesNotExist:
        email_exists = False

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
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    payload: UserLogin
):
    try:
        if await is_email(payload.username_or_email):
            user = await user_repo.get_user_by_email(payload.username_or_email)
        else:
            user = await user_repo.get_user_by_username(payload.username_or_email)
    except UserDoesNotExist:
        await dummy_hash_password()
        raise HTTPException(
            detail="Account does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )

    is_correct_password = await verify_password(payload.password, user.hashed_password)
    if not is_correct_password:
        raise HTTPException(
            detail="Account details wrong",
            status_code=status.HTTP_409_CONFLICT
        )

    if not user.is_email_verified:
        token_service = TokenService(prefix="email_verify")
        await send_verification(
            user_id=str(user.id), 
            name=user.username, 
            email=user.email, 
            token_service=token_service
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. A new verification link has been sent to your email."
        )

    access_token = await create_access_token({"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")
        

@router.get("/verify-email")
@limiter.limit("20/minute")
async def verify_email(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    token_service = TokenService(prefix="email_verify")
    user_id = await token_service.verify_token(token, consume=True)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    try:
        user_id = uuid.UUID(user_id)
        user = await user_repo.get_user_by_id(user_id)
    except UserDoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_email_verified = True
    await db.commit()
    return {"message": "Email verified successfully"}


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id_route(user_id: UUID, current_user: CurrentUser):
    try:
        return await user_repo.get_user_by_id(user_id)
    except UserDoesNotExist:
        raise HTTPException(
            detail="User not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


@router.get("/{username}", response_model=UserResponse)
async def get_user_by_username_route(username: str, current_user: CurrentUser):
    try:
        return await user_repo.get_user_by_username(username)
    except UserDoesNotExist:
        raise HTTPException(
            detail="User not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


@router.patch("/{username}", response_model=UserResponse)
async def edit_username_route(payload: UserUsernameUpdate):
    pass