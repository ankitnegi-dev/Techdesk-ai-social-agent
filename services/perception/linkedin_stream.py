"""
LinkedIn connector — no API key needed.
Uses two sources:
1. Google News RSS for LinkedIn company mentions
2. Public LinkedIn company posts via HTTP
Polls every 5 minutes.
"""
import asyncio
import logging
import hashlib
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import requests
import feedparser
from shared.config import get_settings
from shared.models import SocialSignal, Platform
from shared.kafka_client import get_producer, publish, TOPICS

settings = get_settings()
logging.basicConfig(level=settings.log_level,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("linkedin_stream")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Google News RSS queries — surfaces LinkedIn posts and articles
NEWS_QUERIES = [
    "TechDeskAI customer support",
    "AI help desk software",
    "customer support automation AI",
    "SaaS ticketing system",
    "Zendesk alternative AI",
]

# Keywords to filter relevant content
KEYWORDS = [
    "customer support", "help desk", "ticketing",
    "support software", "ai support", "zendesk",
    "intercom", "freshdesk", "support tool",
    "TechDeskAI", "techdesk",
]

seen_ids = set()

def fetch_google_news(query: str) -> list:
    """Fetch Google News RSS for a query."""
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        feed = feedparser.parse(url)
        return feed.entries[:5]
    except Exception as e:
        log.warning(f"Google News fetch failed for '{query}': {e}")
        return []

def fetch_linkedin_company_posts(company: str) -> list:
    """
    Fetch public LinkedIn company posts via Google cache.
    Returns list of post dicts.
    """
    url = f"https://news.google.com/rss/search?q=site:linkedin.com+{company}&hl=en&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url)
        return feed.entries[:5]
    except Exception as e:
        log.warning(f"LinkedIn fetch failed for {company}: {e}")
        return []

def is_relevant(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in KEYWORDS)

def make_signal_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]

async def poll_linkedin(producer, interval: int = 300):
    log.info("LinkedIn stream started — polling every 5 minutes")
    log.info(f"Queries: {NEWS_QUERIES}")

    while True:
        new_signals = 0

        # Source 1 — Google News RSS
        for query in NEWS_QUERIES:
            entries = fetch_google_news(query)
            for entry in entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                source = entry.get("source", {}).get("title", "news")
                link = entry.get("link", "")

                signal_id = make_signal_id(title)
                if signal_id in seen_ids:
                    continue
                seen_ids.add(signal_id)

                content = title
                if summary and len(summary) > 20:
                    content += f" — {summary[:150]}"

                if not is_relevant(content):
                    continue

                signal = SocialSignal(
                    platform=Platform.LINKEDIN,
                    external_id=f"linkedin_news_{signal_id}",
                    author_id=f"source_{source}",
                    author_username=source,
                    content=content,
                )

                await publish(producer, TOPICS["signals_raw"],
                             signal.model_dump(mode="json"), key=signal.id)
                log.info(f"[LinkedIn/News] {source}: {title[:70]}")
                new_signals += 1

        # Source 2 — LinkedIn company posts via Google
        companies = ["TechDeskAI", "Zendesk", "Intercom", "Freshdesk"]
        for company in companies:
            entries = fetch_linkedin_company_posts(company)
            for entry in entries:
                title = entry.get("title", "")
                signal_id = make_signal_id(title)

                if signal_id in seen_ids:
                    continue
                seen_ids.add(signal_id)

                if not is_relevant(title):
                    continue

                signal = SocialSignal(
                    platform=Platform.LINKEDIN,
                    external_id=f"linkedin_{signal_id}",
                    author_id=f"linkedin_{company}",
                    author_username=company,
                    content=title,
                )

                await publish(producer, TOPICS["signals_raw"],
                             signal.model_dump(mode="json"), key=signal.id)
                log.info(f"[LinkedIn] {company}: {title[:70]}")
                new_signals += 1

        if new_signals > 0:
            log.info(f"Published {new_signals} LinkedIn signals to Kafka")
        else:
            log.info("No new relevant LinkedIn signals found")

        await asyncio.sleep(interval)

async def main():
    producer = await get_producer()
    await poll_linkedin(producer)

if __name__ == "__main__":
    asyncio.run(main())
