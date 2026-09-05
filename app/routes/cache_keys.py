from uuid import UUID


async def get_monitor_lists_cache_key(user_id: UUID):
    return f"{user_id!s}:monitors"


async def get_monitor_cache_key(user_id: UUID, monitor_id: UUID):
    return f"{user_id!s}:{monitor_id!s}:monitor"
