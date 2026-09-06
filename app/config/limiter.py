from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config.settings import REDIS_URL
from app.errors.user_errors import TooManyRequestsError
from app.services.redis_client import redis_client

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
)


async def enforce_send_cooldown(namespace: str, identifier: str, seconds: int) -> None:
    key = f"ratelimit:{namespace}:{identifier.lower()}"
    allowed = await redis_client.set(key, "1", ex=seconds, nx=True)
    if allowed:
        return

    retry_after = await redis_client.ttl(key)
    raise TooManyRequestsError(
        f"Please wait before requesting another {namespace.replace('-', ' ')} email",
        retry_after=max(retry_after, 0),
    )
