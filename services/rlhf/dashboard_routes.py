"""
Phase 5 analytics routes — add to the HITL dashboard FastAPI app.
Shows RLHF stats and strategy leaderboard.
"""
from fastapi import APIRouter
from services.rlhf.collector import get_preference_stats
from services.rlhf.strategy_tracker import get_strategy_leaderboard, record_outcome

router = APIRouter(prefix="/api/rlhf", tags=["rlhf"])

@router.get("/stats")
async def rlhf_stats():
    stats = await get_preference_stats()
    return {"preference_pairs": stats}

@router.get("/leaderboard")
async def strategy_leaderboard():
    board = get_strategy_leaderboard()
    return {"leaderboard": board}

@router.post("/outcome")
async def record_strategy_outcome(intent: str, strategy: str, reward: float):
    record_outcome(intent, strategy, reward)
    return {"status": "recorded", "intent": intent, "strategy": strategy, "reward": reward}
