from uuid import UUID

from app.models.url_monitor import URLMonitor
from app.services.redis_client import redis_client


async def get_monitor_lists_cache_key(user_id: UUID):
    return f"user:{user_id!s}:monitors"


async def get_monitor_cache_key(monitor_id: UUID):
    return f"monitor:{monitor_id!s}"


async def invalidate_monitor_list_caches(user_ids: list[UUID]):
    cache_keys = [
        await get_monitor_lists_cache_key(user_id) for user_id in set(user_ids)
    ]
    if cache_keys:
        await redis_client.delete(*cache_keys)


async def invalidate_monitor_caches(url_monitor: URLMonitor):
    owner_ids: list[UUID] = []

    if url_monitor.owner_user_id is not None:
        owner_ids.append(url_monitor.owner_user_id)

    if url_monitor.owner_group is not None:
        owner_ids.extend(member.id for member in url_monitor.owner_group.members)
        owner_ids.extend(admin.id for admin in url_monitor.owner_group.admins)

    monitor_cache_key = await get_monitor_cache_key(url_monitor.id)
    await redis_client.delete(monitor_cache_key)
    await invalidate_monitor_list_caches(owner_ids)
