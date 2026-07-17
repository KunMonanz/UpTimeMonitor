from sqlalchemy.future import select

from app.config.database_config import SessionLocal
from app.config.security_config import hash_password, verify_password
from app.models.url_monitor import URLMonitor
from app.models.users import User

class UserRepository:
    """Repository for URLMonitor model."""
    
    def __init__(self):
        self.db = SessionLocal()
    
    async def create_user(
        self, 
        username: str, 
        email: str, 
        hashed_password: str
    ) -> User:
        """Create a new user in the database."""
        
        hashed_password = hash_password(hashed_password)
        
        new_user = User(
            username=username, 
            email=email, 
            hashed_password=hashed_password
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user

    async def get_user_by_username(self, username: str) -> User | None:
        """Retrieve a user by their username."""
        
        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
