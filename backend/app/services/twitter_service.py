import logging
import tweepy
from app.config import settings

logger = logging.getLogger(__name__)


def _get_client():
    if not all([
        settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET,
        settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET,
    ]):
        return None
    return tweepy.Client(
        consumer_key=settings.TWITTER_API_KEY,
        consumer_secret=settings.TWITTER_API_SECRET,
        access_token=settings.TWITTER_ACCESS_TOKEN,
        access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET,
    )


def _build_tweet(article: dict) -> str:
    title      = article.get("title", "RedsHub Pick")
    art_type   = article.get("article_type", "prediction")
    slug       = article.get("slug", "")
    picks      = article.get("key_picks") or {}
    url        = f"https://redshub.vercel.app/predictions/{slug}"

    parts = []
    if art_type == "best_bet":
        parts.append("🔴 BEST BET —")
    elif art_type == "prop":
        parts.append("⚾ PROP BET —")
    else:
        parts.append("📊 PREDICTION —")

    parts.append(title[:80])

    if isinstance(picks, dict):
        if picks.get("spread_pick"):
            parts.append(f"RL: {picks['spread_pick']} {picks.get('spread_lean','')}")
        if picks.get("total_pick"):
            parts.append(f"O/U: {picks['total_pick']} {picks.get('total_lean','')}")
        if picks.get("confidence"):
            parts.append(f"🎯 {picks['confidence']} Confidence")

    parts.append(url)
    parts.append("#Reds #CincinnatiReds #MLB")

    tweet = "\n".join(parts)
    return tweet[:280]


async def post_article_tweet(article: dict) -> str:
    client = _get_client()
    if not client:
        raise ValueError("Twitter credentials not configured")
    tweet_text = _build_tweet(article)
    resp = client.create_tweet(text=tweet_text)
    tweet_id = resp.data["id"]
    return f"https://twitter.com/i/web/status/{tweet_id}"
