import asyncio
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.config import get_settings
from shared.models import SocialSignal, Platform
from shared.kafka_client import get_producer, publish, TOPICS

settings = get_settings()
logging.basicConfig(level=settings.log_level,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("perception")

async def simulate_stream():
    log.info("TechDesk AI — SIMULATION MODE — publishing to Kafka every 30 seconds")
    producer = await get_producer()
    log.info("Kafka producer ready")

    samples = [
        ("dev_rajesh",      "Hey @TechDeskAI your Slack integration keeps disconnecting every hour. Super annoying!"),
        ("startup_priya",   "Just switched to @TechDeskAI from Zendesk and honestly blown away. The AI suggestions are incredible!"),
        ("pm_arjun",        "@TechDeskAI do you support integration with HubSpot CRM? We need ticket data to sync both ways."),
        ("agency_meera",    "@TechDeskAI is there a limit on how many automations we can create on the Growth plan?"),
        ("angry_customer",  "@TechDeskAI this is unacceptable. Our entire support inbox has been down for 2 hours and no response from your team!!!!"),
        ("student_karan",   "Using @TechDeskAI for my internship project and the API docs are seriously the best I have seen. Keep it up!"),
        ("cto_vikram",      "@TechDeskAI what encryption standard do you use for data at rest? We need SOC 2 compliance details."),
        ("user_sneha",      "The mobile app for @TechDeskAI crashed when I tried to assign a ticket. iPhone 15 iOS 17."),
    ]

    i = 0
    try:
        while True:
            username, content = samples[i % len(samples)]
            signal = SocialSignal(
                platform=Platform.TWITTER,
                external_id=f"techdesk_sim_{i}",
                author_id=f"user_{i}",
                author_username=username,
                content=content,
            )
            await publish(producer, TOPICS["signals_raw"],
                         signal.model_dump(mode="json"), key=signal.id)
            log.info(f"[SIM] Published: {content[:75]}")
            i += 1
            await asyncio.sleep(30)
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(simulate_stream())
