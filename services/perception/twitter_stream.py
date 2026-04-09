import asyncio
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import tweepy
from shared.config import get_settings
from shared.models import SocialSignal, Platform
from shared.kafka_client import get_producer, publish, TOPICS
from services.perception.normalizer import normalize_twitter

settings = get_settings()
logging.basicConfig(level=settings.log_level,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("twitter_stream")

TRACK_KEYWORDS = ["@TechDeskAI", "#TechDeskAI", "TechDeskAI"]

class TechDeskStreamListener(tweepy.StreamingClient):
    def __init__(self, bearer_token: str, producer, loop):
        super().__init__(bearer_token)
        self._producer = producer
        self._loop = loop

    def on_tweet(self, tweet: tweepy.Tweet):
        log.info(f"Real tweet received: {tweet.text[:80]}")
        try:
            author = {
                "id": str(tweet.author_id or ""),
                "username": str(tweet.author_id or "unknown"),
            }
            signal = normalize_twitter(tweet.data, author)
            asyncio.run_coroutine_threadsafe(
                publish(self._producer, TOPICS["signals_raw"],
                        signal.model_dump(mode="json"), key=signal.id),
                self._loop
            )
            log.info(f"Published to Kafka: {signal.content[:70]}")
        except Exception as e:
            log.error(f"Error processing tweet: {e}")

    def on_errors(self, errors):
        log.error(f"Stream errors: {errors}")

    def on_connection_error(self):
        log.warning("Connection error — reconnecting...")


def setup_rules(client: tweepy.StreamingClient):
    existing = client.get_rules()
    if existing.data:
        ids = [rule.id for rule in existing.data]
        client.delete_rules(ids)
        log.info(f"Deleted {len(ids)} old rules")
    for keyword in TRACK_KEYWORDS:
        client.add_rules(tweepy.StreamRule(keyword))
        log.info(f"Added rule: {keyword}")


async def start_twitter_stream():
    producer = await get_producer()
    loop = asyncio.get_event_loop()

    stream = TechDeskStreamListener(
        bearer_token=settings.twitter_bearer_token,
        producer=producer,
        loop=loop,
    )

    setup_rules(stream)
    log.info("Starting real Twitter filtered stream...")
    log.info(f"Tracking: {TRACK_KEYWORDS}")
    log.info("Waiting for real tweets — post a tweet mentioning @TechDeskAI to test!")

    stream.filter(
        tweet_fields=["author_id", "created_at", "public_metrics"],
        expansions=["author_id"],
    )


if __name__ == "__main__":
    asyncio.run(start_twitter_stream())
