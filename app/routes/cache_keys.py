from uuid import UUID

from app.models.url_monitor import URLMonitor
from app.services.redis_client import redis_client


async def get_monitor_lists_cache_key(user_id: UUID, offset: int, limit: int):
    return f"user:{user_id!s}:monitors:{offset}:{limit}"


async def get_monitor_cache_key(monitor_id: UUID):
    return f"monitor:{monitor_id!s}"


async def get_group_cache_key(group_id: UUID):
    return f"group:{group_id!s}"


async def get_group_members_cache_key(group_id: UUID, offset: int, limit: int):
    return f"group:{group_id!s}:members:{offset}:{limit}"


async def get_group_monitors_cache_key(group_id: UUID, offset: int, limit: int):
    return f"group:{group_id!s}:monitors:{offset}:{limit}"


async def get_user_cache_key(user_id: UUID):
    return f"user:{user_id!s}:detail"


async def get_user_by_username_cache_key(username: str):
    return f"user:username:{username.lower()}"


async def _delete_pattern(pattern: str):
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)


async def invalidate_monitor_list_caches(user_ids: list[UUID]):
    for user_id in set(user_ids):
        await _delete_pattern(f"user:{user_id!s}:monitors:*")


async def invalidate_group_caches(
    group_id: UUID, affected_user_ids: list[UUID] | None = None
):
    await redis_client.delete(await get_group_cache_key(group_id))
    await _delete_pattern(f"group:{group_id!s}:members:*")
    await _delete_pattern(f"group:{group_id!s}:monitors:*")
    if affected_user_ids:
        await invalidate_monitor_list_caches(affected_user_ids)


async def invalidate_monitor_caches(url_monitor: URLMonitor):
    owner_ids: list[UUID] = []

    if url_monitor.owner_user_id is not None:
        owner_ids.append(url_monitor.owner_user_id)

    if url_monitor.owner_group is not None:
        owner_ids.extend(member.id for member in url_monitor.owner_group.members)
        owner_ids.extend(admin.id for admin in url_monitor.owner_group.admins)
        if url_monitor.owner_group_id is not None:
            await invalidate_group_caches(url_monitor.owner_group_id, owner_ids)

    monitor_cache_key = await get_monitor_cache_key(url_monitor.id)
    await redis_client.delete(monitor_cache_key)
    await invalidate_monitor_list_caches(owner_ids)
