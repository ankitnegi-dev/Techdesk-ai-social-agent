import uuid
import logging
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Float
from sqlalchemy.ext.asyncio import AsyncSession
from shared.db.models import Base, AsyncSessionLocal

log = logging.getLogger("rlhf")

class PreferencePair(Base):
    __tablename__ = "preference_pairs"
    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id       = Column(String)
    account_id      = Column(String(64))
    intent          = Column(String(64))
    prompt          = Column(Text)
    agent_draft     = Column(Text)
    human_edit      = Column(Text)
    was_edited      = Column(String(8))
    sentiment_score = Column(Float, default=0.0)
    created_at      = Column(DateTime, default=datetime.utcnow)

async def record_preference(
    signal_id: str,
    intent: str,
    prompt: str,
    agent_draft: str,
    human_edit: str,
    was_edited: str = "yes",
    sentiment_score: float = 0.0,
    account_id: str = "demo_account",
):
    try:
        async with AsyncSessionLocal() as db:
            pair = PreferencePair(
                signal_id=signal_id,
                account_id=account_id,
                intent=intent,
                prompt=prompt,
                agent_draft=agent_draft,
                human_edit=human_edit,
                was_edited=was_edited,
                sentiment_score=sentiment_score,
            )
            db.add(pair)
            await db.commit()
            log.info(f"RLHF pair saved — intent={intent} edited={was_edited}")
    except Exception as e:
        log.warning(f"RLHF record failed: {e}")

async def get_preference_stats() -> dict:
    from sqlalchemy import select, func
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(
                    PreferencePair.intent,
                    PreferencePair.was_edited,
                    func.count(PreferencePair.id).label("count")
                ).group_by(PreferencePair.intent, PreferencePair.was_edited)
            )
            rows = result.fetchall()
            return {f"{r.intent}:{r.was_edited}": r.count for r in rows}
    except Exception as e:
        log.warning(f"Stats query failed: {e}")
        return {}
