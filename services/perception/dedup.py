"""
Deduplication helper — stores seen signal IDs in Redis.
Prevents re-publishing the same post when perception restarts.
"""
import redis
from shared.config import get_settings

settings = get_settings()

def is_seen(signal_id: str) -> bool:
    r = redis.from_url(settings.redis_url, decode_responses=True)
    seen = r.sismember("perception:seen_ids", signal_id)
    r.close()
    return seen

def mark_seen(signal_id: str, ttl_days: int = 7):
    r = redis.from_url(settings.redis_url, decode_responses=True)
    r.sadd("perception:seen_ids", signal_id)
    r.expire("perception:seen_ids", ttl_days * 86400)
    r.close()
