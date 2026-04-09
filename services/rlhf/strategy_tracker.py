import json
import logging
import redis
from shared.config import get_settings

settings = get_settings()
log = logging.getLogger("strategy")

STRATEGIES = {
    "complaint":          ["empathy_first", "solution_first", "escalate_always"],
    "praise":             ["warm_thanks", "amplify", "brief_ack"],
    "question":           ["rag_answer", "direct_answer", "ask_for_details"],
    "viral_opportunity":  ["unique_angle", "join_conversation", "tag_accounts"],
}

EPSILON = 0.2

def _redis_key(intent: str, strategy: str) -> str:
    return f"strategy:{intent}:{strategy}"

def get_best_strategy(intent: str) -> str:
    import random
    strategies = STRATEGIES.get(intent, ["default"])
    if len(strategies) == 1:
        return strategies[0]
    if random.random() < EPSILON:
        chosen = random.choice(strategies)
        log.debug(f"[Explore] {intent} → {chosen}")
        return chosen
    r = redis.from_url(settings.redis_url, decode_responses=True)
    best_strategy = strategies[0]
    best_score = -1.0
    for strategy in strategies:
        data = r.get(_redis_key(intent, strategy))
        if data:
            stats = json.loads(data)
            count = stats.get("count", 0)
            total = stats.get("total_reward", 0.0)
            avg = total / count if count > 0 else 0.0
            if avg > best_score:
                best_score = avg
                best_strategy = strategy
    r.close()
    log.debug(f"[Exploit] {intent} → {best_strategy} (score={best_score:.2f})")
    return best_strategy

def record_outcome(intent: str, strategy: str, reward: float):
    r = redis.from_url(settings.redis_url, decode_responses=True)
    key = _redis_key(intent, strategy)
    data = r.get(key)
    stats = json.loads(data) if data else {"count": 0, "total_reward": 0.0}
    stats["count"] += 1
    stats["total_reward"] += reward
    r.set(key, json.dumps(stats))
    r.close()
    avg = stats["total_reward"] / stats["count"]
    log.info(f"Strategy: {intent}/{strategy} reward={reward:.1f} avg={avg:.2f} n={stats['count']}")

def get_strategy_leaderboard() -> dict:
    r = redis.from_url(settings.redis_url, decode_responses=True)
    leaderboard = {}
    for intent, strategies in STRATEGIES.items():
        leaderboard[intent] = []
        for strategy in strategies:
            data = r.get(_redis_key(intent, strategy))
            if data:
                stats = json.loads(data)
                count = stats.get("count", 0)
                avg = stats["total_reward"] / count if count > 0 else 0.0
            else:
                count, avg = 0, 0.0
            leaderboard[intent].append({"strategy": strategy, "avg_reward": round(avg, 3), "count": count})
        leaderboard[intent].sort(key=lambda x: x["avg_reward"], reverse=True)
    r.close()
    return leaderboard
