import json
import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from shared.config import get_settings

settings = get_settings()
log = logging.getLogger("kafka")

KAFKA_BOOTSTRAP = "localhost:9092"

TOPICS = {
    "signals_raw":        "social.signals.raw",
    "signals_classified": "social.signals.classified",
    "actions_draft":      "agent.actions.draft",
    "actions_approved":   "agent.actions.approved",
    "actions_published":  "agent.actions.published",
}

async def get_producer() -> AIOKafkaProducer:
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )
    await producer.start()
    return producer

async def get_consumer(topic: str, group_id: str) -> AIOKafkaConsumer:
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=group_id,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await consumer.start()
    return consumer

async def publish(producer: AIOKafkaProducer, topic: str, message: dict, key: str = None):
    await producer.send_and_wait(topic, value=message, key=key)
    log.debug(f"Published to {topic}: {str(message)[:80]}")
