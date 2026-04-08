from pathlib import Path
import sys

REPO_ROOT = Path(r"/Users/hitesh/bug-investigator/inputs/mini_repo").resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import asyncio
from client import fetch_profile
from cache import CACHE

async def main():
    user_id = 'new_user'
    profile = CACHE.get(user_id)
    if profile is None:
        # Simulate the bug by not awaiting the async function call
        profile = fetch_profile(user_id)  # Missing await here
        CACHE[user_id] = profile
    tier = profile['tier']
    print(f'Tier for {user_id}:', tier)

asyncio.run(main())