"""
X (Twitter) auto-posting for Zapway Newsroom.

After an article is successfully published to zapway.app, a short update is
posted to X. This is DISABLED unless all four X API credentials are set as
environment variables (get them from https://developer.x.com — a project/app
with OAuth 1.0a "Read and Write" permission):

  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET

Without them, post_to_x() returns {"success": False, "skipped": True} and the
publish flow continues normally.
"""
import os
import re


def _get_client():
    ck = os.getenv("X_API_KEY")
    cs = os.getenv("X_API_SECRET")
    at = os.getenv("X_ACCESS_TOKEN")
    ats = os.getenv("X_ACCESS_TOKEN_SECRET")
    if not all([ck, cs, at, ats]):
        return None, "X API credentials not set (X_API_KEY/X_API_SECRET/X_ACCESS_TOKEN/X_ACCESS_TOKEN_SECRET)."
    try:
        import tweepy
    except ImportError:
        return None, "tweepy is not installed (add it to requirements.txt)."
    try:
        client = tweepy.Client(
            consumer_key=ck, consumer_secret=cs,
            access_token=at, access_token_secret=ats,
        )
        return client, None
    except Exception as e:
        return None, f"Failed to init X client: {e}"


def build_caption(title: str, summary: str = "", hashtags=None) -> str:
    """Build a concise, on-brand X caption from an article."""
    title = (title or "").strip()
    tags = hashtags or ["#EVNews", "#India", "#ZAPWAY"]
    tag_str = " ".join(tags)
    # Leave room for a URL (X counts any link as 23 chars) + hashtags.
    room = 280 - 24 - len(tag_str) - 4
    caption = title
    if summary:
        extra = " — " + summary.strip()
        if len(caption) + len(extra) <= room:
            caption += extra
    if len(caption) > room:
        caption = caption[:room - 1].rstrip() + "…"
    return f"⚡ {caption}\n\n{tag_str}"


def post_to_x(text: str, url: str = None) -> dict:
    """Post a short update (optionally with a link) to X/Twitter.

    Returns {"success": bool, "tweet_id"?: str, "error"?: str, "skipped"?: bool}.
    """
    client, err = _get_client()
    if not client:
        return {"success": False, "error": err, "skipped": True}

    tweet = (text or "").strip()
    if url and url.startswith("http") and url not in tweet:
        tweet = f"{tweet}\n{url}"
    # Hard cap (X counts a URL as 23 chars, but tweepy/API will validate).
    if len(tweet) > 280 and not url:
        tweet = tweet[:279].rstrip() + "…"
    try:
        resp = client.create_tweet(text=tweet)
        tid = None
        if getattr(resp, "data", None):
            tid = resp.data.get("id")
        return {"success": True, "tweet_id": tid}
    except Exception as e:
        return {"success": False, "error": str(e)}
