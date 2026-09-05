from uuid import UUID


def get_monnitor_lists_cache_key(user_id: UUID):
    return f"{user_id!s}:monitors"
