import asyncio
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.config import get_settings
from shared.kafka_client import get_producer

settings = get_settings()
logging.basicConfig(level=settings.log_level,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("launcher")

async def main():
    log.info("=" * 55)
    log.info("TechDesk AI — Perception Launcher")
    log.info("Starting all platform connectors...")
    log.info("=" * 55)

    producer = await get_producer()

    from services.perception.reddit_stream import poll_reddit
    from services.perception.linkedin_stream import poll_linkedin

    tasks = [
        asyncio.create_task(poll_reddit(producer, interval=60)),
        asyncio.create_task(poll_linkedin(producer, interval=300)),
    ]

    simulation_mode = os.getenv("SIMULATION_MODE", "false").lower() == "true"
    if simulation_mode:
        from services.perception.main import simulate_stream
        tasks.append(asyncio.create_task(simulate_stream()))
        log.info("Simulation mode: ON")
    else:
        log.info("Simulation mode: OFF (set SIMULATION_MODE=true to enable)")

    log.info(f"Running {len(tasks)} perception connectors")
    log.info("  Reddit   — polling every 60 seconds")
    log.info("  LinkedIn — polling every 5 minutes")

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
