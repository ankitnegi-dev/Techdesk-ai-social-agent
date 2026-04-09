"""
Append-only audit trail — logs every LLM call, tool call,
and publish event to PostgreSQL. 12-month retention.
"""
import uuid
import logging
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.ext.asyncio import AsyncSession
from shared.db.models import Base, AsyncSessionLocal

log = logging.getLogger("audit")

class AuditLog(Base):
    __tablename__ = "audit_log"
    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type  = Column(String(64))   # llm_call | tool_call | publish | safety_check
    account_id  = Column(String(64))
    signal_id   = Column(String, nullable=True)
    action_id   = Column(String, nullable=True)
    agent_id    = Column(String(64), nullable=True)
    payload     = Column(JSON)         # full prompt+response or tool I/O
    created_at  = Column(DateTime, default=datetime.utcnow)

async def log_event(
    event_type: str,
    payload: dict,
    account_id: str = "demo_account",
    signal_id: str = None,
    action_id: str = None,
    agent_id: str = None,
):
    """Write one audit entry. Never raises — audit failures must not block the agent."""
    try:
        async with AsyncSessionLocal() as db:
            entry = AuditLog(
                event_type=event_type,
                account_id=account_id,
                signal_id=signal_id,
                action_id=action_id,
                agent_id=agent_id,
                payload=payload,
            )
            db.add(entry)
            await db.commit()
    except Exception as e:
        log.warning(f"Audit log failed (non-blocking): {e}")

async def log_llm_call(agent_id: str, prompt: str, response: str, signal_id: str = None):
    await log_event(
        event_type="llm_call",
        agent_id=agent_id,
        signal_id=signal_id,
        payload={"prompt_preview": prompt[:500], "response_preview": response[:500]},
    )

async def log_safety_check(action_id: str, passed: bool, score: float, flags: list):
    await log_event(
        event_type="safety_check",
        action_id=action_id,
        payload={"passed": passed, "toxicity_score": score, "flags": flags},
    )

async def log_publish(action_id: str, platform: str, content: str):
    await log_event(
        event_type="publish",
        action_id=action_id,
        payload={"platform": platform, "content": content},
    )
