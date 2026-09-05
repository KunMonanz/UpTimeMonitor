from uuid import UUID

from app.services.redis_client import redis_client


async def get_monitor_lists_cache_key(user_id: UUID):
    return f"{user_id!s}:monitors"


async def get_monitor_cache_key(user_id: UUID, monitor_id: UUID):
    return f"{user_id!s}:{monitor_id!s}:monitor"


async def invalidate_monitor_caches(user_id: UUID, monitor_id: UUID):
    monitor_cache_key = await get_monitor_cache_key(user_id, monitor_id)
    monitor_list_cache_key = await get_monitor_lists_cache_key(user_id)
    await redis_client.delete(monitor_cache_key, monitor_list_cache_key)
