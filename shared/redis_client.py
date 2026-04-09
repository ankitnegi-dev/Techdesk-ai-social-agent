import redis.asyncio as aioredis
import redis as syncredis
import json
from shared.config import get_settings

settings = get_settings()

async def get_redis():
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()

def get_sync_redis():
    return syncredis.from_url(settings.redis_url, decode_responses=True)

async def push_signal(client, signal_dict: dict):
    await client.lpush("queue:signals", json.dumps(signal_dict))

async def pop_signal(client) -> dict | None:
    result = await client.brpop("queue:signals", timeout=5)
    if result:
        return json.loads(result[1])
    return None

async def push_action(client, action_dict: dict):
    await client.lpush("queue:hitl_review", json.dumps(action_dict))

async def set_working_memory(client, session_id: str, data: dict, ttl: int = 3600):
    await client.setex(f"wm:{session_id}", ttl, json.dumps(data))

async def get_working_memory(client, session_id: str) -> dict:
    raw = await client.get(f"wm:{session_id}")
    return json.loads(raw) if raw else {}
