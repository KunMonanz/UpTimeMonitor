from pydantic import EmailStr
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config.database_config import SessionLocal
from app.errors.user_errors import UserDoesNotExist
from app.models.users import User


class UserRepository:
    """Repository for URLMonitor model."""

    def __init__(self, db: AsyncSession):
        self.db = SessionLocal()

    async def create_user(
        self, username: str, email: str, hashed_password: str
    ) -> User:
        """Create a new user in the database."""
        username = username.lower()

        new_user = User(username=username, email=email, hashed_password=hashed_password)
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user

    async def get_user_by_username(self, username: str) -> User:
        """Retrieve a user by their username."""
        username = username.lower()

        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        try:
            return result.scalar_one()
        except NoResultFound:
            raise UserDoesNotExist("User not found")

    async def get_user_by_id(self, user_id) -> User:
        """Retrieve a user by their di."""

        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        try:
            return result.scalar_one()
        except NoResultFound:
            raise UserDoesNotExist("User not found")

    async def get_user_by_email(self, email: EmailStr) -> User:
        """Retrieve a user by their di."""

        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        try:
            return result.scalar_one()
        except NoResultFound:
            raise UserDoesNotExist("User not found")

    async def edit_username(self):
        pass
