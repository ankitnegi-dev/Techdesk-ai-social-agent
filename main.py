import asyncio
import logging
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from shared.config import get_settings
from shared.models import SocialSignal, PersonaConfig, Platform, ActionType, AgentAction
from shared.kafka_client import get_producer, get_consumer, publish, TOPICS
from shared.audit import log_event, log_safety_check
from services.agents.graph import run_graph
from services.safety.gate import run_safety_gate
from shared.db.models import AsyncSessionLocal, init_db
from services.rag.pipeline import retrieve_context

settings = get_settings()
logging.basicConfig(level=settings.log_level,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("main")

DEFAULT_PERSONA = PersonaConfig(
    account_id="techdesk_ai_twitter",
    display_name="TechDesk AI",
    platform=Platform.TWITTER,
    tone_primary="friendly",
    tone_secondary="helpful",
    voice_examples=[
        "Hey! Sorry you are running into that — let us get it sorted. Can you DM us your account email so we can take a look?",
        "That is awesome to hear, thank you! We work really hard on making things smooth for you. Means a lot!",
        "Great question! You can connect your tools under Settings > Integrations > Add New. Takes about 2 minutes to set up!",
        "We totally get the frustration — that should not be happening. Can you share a screenshot so we can dig in faster?",
        "Glad it is working well for you! If you want to explore advanced features, check out our guide at docs.techdesk.ai",
    ],
    topics=[
        "product support", "bug reports", "feature requests",
        "onboarding help", "integration questions", "billing and pricing",
        "account management", "AI assistant features", "API questions",
    ],
    avoid_topics=[
        "politics", "religion", "competitor names",
        "legal disputes", "unreleased features",
    ],
    approved_hashtags=[
        "#TechDeskAI", "#CustomerSupport", "#AISupport", "#TechSupport",
    ],
    max_posts_per_day=30,
    min_gap_hours=0.5,
    approval_required=True,
)

async def process_signal(signal: SocialSignal, producer: AIOKafkaProducer):
    """Full Phase 4 pipeline for one signal."""

    # Step 1 — RAG context retrieval
    rag_context = []
    try:
        async with AsyncSessionLocal() as db:
            rag_context = await retrieve_context(signal.content, db, top_k=3)
    except Exception as e:
        log.warning(f"RAG failed: {e}")

    # Step 2 — Run LangGraph multi-agent pipeline
    result = await run_graph(
        signal=signal.model_dump(mode="json"),
        persona=DEFAULT_PERSONA.model_dump(mode="json"),
        rag_context=rag_context,
    )

    draft        = result.get("draft_content", "")
    action_type  = result.get("action_type", "reply")
    intent       = result.get("intent", "unknown")
    sentiment    = result.get("sentiment", 0.0)
    route        = result.get("route_to", "engagement")

    log.info(f"    Agent    : {route} | Intent: {intent} | Sentiment: {sentiment:+.2f}")
    log.info(f"    Draft    : {draft[:150]}")

    # Step 3 — Publish draft to Kafka
    action = AgentAction(
        signal_id=signal.id,
        agent_id=f"{route}_agent_v4",
        action_type=ActionType(action_type)
            if action_type in ActionType._value2member_map_
            else ActionType.ESCALATE,
        draft_content=draft,
    )

    await publish(producer, TOPICS["actions_draft"], action.model_dump(mode="json"), key=signal.id)

    # Step 4 — Safety gate
    if action.action_type != ActionType.ESCALATE:
        mod = await run_safety_gate(draft, DEFAULT_PERSONA)
        action.moderation = mod

        # Audit the safety check
        await log_safety_check(
            action_id=action.id,
            passed=mod.passed,
            score=mod.perspective_score,
            flags=mod.flags,
        )

        if not mod.passed:
            action.action_type = ActionType.ESCALATE
            log.warning(f"    BLOCKED  : {mod.reason}")
        else:
            log.info(f"    Safety   : PASSED (toxicity={mod.perspective_score:.2f})")

    # Step 5 — Route to approved or HITL queue
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.redis_url, decode_responses=True)

    if action.action_type == ActionType.ESCALATE or settings.hitl_enabled:
        await r.lpush("queue:hitl_review", action.model_dump_json())
        log.info(f"    Status   : → HITL REVIEW QUEUE")
    else:
        await publish(producer, TOPICS["actions_approved"],
                      action.model_dump(mode="json"), key=signal.id)
        log.info(f"    Status   : → KAFKA actions.approved")

    # Step 6 — Audit the full action
    await log_event(
        event_type="agent_action",
        signal_id=signal.id,
        action_id=action.id,
        agent_id=action.agent_id,
        payload={
            "intent": intent,
            "sentiment": sentiment,
            "draft": draft[:300],
            "action_type": action.action_type.value,
        },
    )
    await r.aclose()

async def main():
    log.info("=" * 60)
    log.info("AI Social Agent — Phase 4 — Kafka + Audit Trail")
    log.info(f"Persona  : {DEFAULT_PERSONA.display_name}")
    log.info(f"HITL     : {'ON' if settings.hitl_enabled else 'OFF'}")
    log.info("=" * 60)

    # Init DB (creates audit_log table)
    await init_db()

    # Start Kafka producer
    producer = await get_producer()
    log.info("Kafka producer connected")

    # Consume from Kafka signals topic
    consumer = await get_consumer(TOPICS["signals_raw"], group_id="main-agent")
    log.info(f"Consuming from Kafka topic: {TOPICS['signals_raw']}")

    processed = 0
    try:
        async for msg in consumer:
            try:
                data = msg.value
                signal = SocialSignal(**data)
                processed += 1
                log.info(f"\n{'─'*55}")
                log.info(f"[{processed}] @{signal.author_username}: {signal.content[:70]}")
                await process_signal(signal, producer)
            except Exception as e:
                await asyncio.sleep(2)  # Rate limit protection
                log.error(f"Error processing message: {e}", exc_info=True)
    except asyncio.CancelledError:
        pass
    finally:
        await consumer.stop()
        await producer.stop()
        log.info("Shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
