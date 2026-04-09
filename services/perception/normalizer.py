from shared.models import SocialSignal, Platform, EngagementMetrics
from datetime import datetime

def normalize_twitter(tweet: dict, author: dict) -> SocialSignal:
    public_metrics = tweet.get("public_metrics", {})
    return SocialSignal(
        platform=Platform.TWITTER,
        external_id=tweet["id"],
        author_id=author.get("id", ""),
        author_username=author.get("username", ""),
        content=tweet.get("text", ""),
        media_urls=[],
        engagement=EngagementMetrics(
            likes=public_metrics.get("like_count", 0),
            replies=public_metrics.get("reply_count", 0),
            shares=public_metrics.get("retweet_count", 0),
            impressions=public_metrics.get("impression_count", 0),
        ),
        parent_id=tweet.get("referenced_tweets", [{}])[0].get("id") if tweet.get("referenced_tweets") else None,
        created_at=_parse_twitter_date(tweet.get("created_at", "")),
    )

def normalize_reddit(post: dict) -> SocialSignal:
    return SocialSignal(
        platform=Platform.REDDIT,
        external_id=post.get("id", ""),
        author_id=post.get("author_id", ""),
        author_username=post.get("author", "[deleted]"),
        content=post.get("selftext") or post.get("body", ""),
        engagement=EngagementMetrics(
            likes=post.get("score", 0),
            replies=post.get("num_comments", 0),
        ),
        created_at=datetime.utcfromtimestamp(post.get("created_utc", 0)),
    )

def _parse_twitter_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    except (ValueError, TypeError):
        return datetime.utcnow()
