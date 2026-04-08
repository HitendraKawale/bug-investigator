import asyncio


async def fetch_profile(user_id: str) -> dict:
    await asyncio.sleep(0)
    return {"tier": "free" if user_id.startswith("new_") else "pro"}
