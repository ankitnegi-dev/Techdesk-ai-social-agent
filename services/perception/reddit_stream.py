import asyncio
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import requests
from shared.config import get_settings
from shared.models import SocialSignal, Platform
from shared.kafka_client import get_producer, publish, TOPICS
from services.perception.dedup import is_seen, mark_seen

settings = get_settings()
logging.basicConfig(level=settings.log_level,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("reddit_stream")

HEADERS = {"User-Agent": "TechDeskAI-Student-Project/1.0"}

SUBREDDITS = [
    "techsupport", "SaaS", "startups",
    "customerservice", "artificial",
]

KEYWORDS = [
    "customer support", "help desk", "ticketing system",
    "support tool", "ai support", "zendesk", "intercom",
    "TechDeskAI", "techdesk", "support software",
]

def fetch_subreddit_posts(subreddit: str, limit: int = 10) -> list:
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()["data"]["children"]
        return []
    except Exception as e:
        log.warning(f"Failed to fetch r/{subreddit}: {e}")
        return []

def is_relevant(title: str, body: str) -> bool:
    text = (title + " " + body).lower()
    return any(kw.lower() in text for kw in KEYWORDS)

async def poll_reddit(producer, interval: int = 60):
    log.info("Reddit stream started — polling every 60 seconds")
    log.info(f"Monitoring: {SUBREDDITS}")

    while True:
        new_signals = 0
        for subreddit in SUBREDDITS:
            posts = fetch_subreddit_posts(subreddit)
            for post in posts:
                data = post["data"]
                post_id = data.get("id", "")
                redis_key = f"reddit_{post_id}"

                if is_seen(redis_key):
                    continue

                title = data.get("title", "")
                body = data.get("selftext", "")
                author = data.get("author", "unknown")

                if not is_relevant(title, body):
                    mark_seen(redis_key)
                    continue

                content = title
                if body and len(body) > 10:
                    content += f" — {body[:200]}"

                signal = SocialSignal(
                    platform=Platform.REDDIT,
                    external_id=f"reddit_{post_id}",
                    author_id=f"reddit_{author}",
                    author_username=author,
                    content=content,
                )

                await publish(producer, TOPICS["signals_raw"],
                             signal.model_dump(mode="json"), key=signal.id)
                mark_seen(redis_key)
                log.info(f"[r/{subreddit}] @{author}: {title[:70]}")
                new_signals += 1

        if new_signals > 0:
            log.info(f"Published {new_signals} Reddit signals to Kafka")
        else:
            log.info(f"Polled {len(SUBREDDITS)} subreddits — no new relevant posts")

        await asyncio.sleep(interval)

async def main():
    producer = await get_producer()
    await poll_reddit(producer)

if __name__ == "__main__":
    asyncio.run(main())
