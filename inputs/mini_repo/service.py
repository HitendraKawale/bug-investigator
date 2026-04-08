from cache import CACHE
from client import fetch_profile


def get_user_tier(user_id: str) -> str:
    profile = CACHE.get(user_id)
    if profile is None:
        profile = fetch_profile(user_id)  # BUG: missing await
        CACHE[user_id] = profile
    return profile["tier"]
