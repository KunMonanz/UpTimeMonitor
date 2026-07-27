import secrets
from datetime import timedelta
from app.services.redis_client import redis_client
from app.config.settings import TOKEN_TTL_SECONDS

if not TOKEN_TTL_SECONDS:
    raise ValueError("TOKEN_TTL_SECOND is missing from settings")

class TokenService:
    def __init__(self, redis=redis_client, prefix: str = "verify_token"):
        self.redis = redis
        self.prefix = prefix

    def _key(self, token: str) -> str:
        return f"{self.prefix}:{token}"

    async def generate_token(self, identifier: str, ttl: int = TOKEN_TTL_SECONDS) -> str:
        """Creates a token and maps it to an identifier (e.g. user_id or email)."""
        token = secrets.token_urlsafe(32)
        await self.redis.set(self._key(token), identifier, ex=ttl)
        return token

    async def verify_token(self, token: str, consume: bool = True) -> str | None:
        """
        Returns the identifier if valid, else None.
        consume=True deletes the token after successful verification (one-time use).
        """
        key = self._key(token)
        identifier = await self.redis.get(key)
        if identifier is None:
            return None
        if consume:
            await self.redis.delete(key)
        if isinstance(identifier, bytes):
            identifier = identifier.decode()
        return identifier