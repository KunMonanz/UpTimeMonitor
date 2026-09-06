from uuid import UUID

from pydantic import EmailStr
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.errors.user_errors import UserDoesNotExist
from app.models.users import User


class UserRepository:
    """Repository for user model."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(
        self, username: str, email: str, hashed_password: str
    ) -> User:
        username = username.lower()

        new_user = User(username=username, email=email, hashed_password=hashed_password)
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user

    async def get_user_by_username(self, username: str) -> User:
        username = username.lower()

        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        try:
            return result.scalar_one()
        except NoResultFound:
            raise UserDoesNotExist("User not found")

    async def get_user_by_id(self, user_id: UUID) -> User:
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        try:
            return result.scalar_one()
        except NoResultFound:
            raise UserDoesNotExist("User not found")

    async def get_user_by_email(self, email: EmailStr) -> User:
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        try:
            return result.scalar_one()
        except NoResultFound:
            raise UserDoesNotExist("User not found")

    async def edit_username(self):
        pass
