import os
import time
import aiohttp
import asyncio
from dateutil import parser
import logging

logger = logging.getLogger("gnews_worker")

async def scrape_gnews(domain_or_query: str):
    """
    Worker using GNews API to fetch EV news.
    """
    results = []
    
    api_key = os.environ.get("GNEWS_API_KEY")
    if not api_key:
        logger.warning("[GNews] GNEWS_API_KEY not found in environment. Skipping.")
        return results

    if domain_or_query in ["newsapi", "newsdata", "gnews", "gnews_global", "gnews_india"]:
        is_global = "global" in domain_or_query.lower() or domain_or_query == "gnews"
        domain_or_query = ""
    else:
        is_global = True

    query = domain_or_query if domain_or_query else "electric vehicle OR EV"
    params = {
        "apikey": api_key,
        "q": query,
        "lang": "en",
        "max": 30
    }
    if not is_global:
        params["country"] = "in"

    url = "https://gnews.io/api/v4/search"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get("articles", [])
                    
                    for article in articles:
                        content = article.get("content") or article.get("description")
                        if not content:
                            continue
                            
                        title = article.get("title", "")
                        link = article.get("url", "")
                        source_name = article.get("source", {}).get("name", "GNews")
                        author = source_name
                        
                        dt_str = article.get("publishedAt", "")
                        try:
                            timestamp = int(parser.parse(dt_str).timestamp()) if dt_str else int(time.time())
                        except:
                            timestamp = int(time.time())
                            
                        results.append({
                            "title": title,
                            "content_raw": content,
                            "source": source_name,
                            "source_type": "gnews",
                            "author": author,
                            "timestamp": timestamp,
                            "url": link,
                            "engagement": {
                                "likes": 0,
                                "comments": 0,
                                "shares": 0
                            }
                        })
                else:
                    text = await response.text()
                    logger.error(f"[GNews] Error fetching data: {response.status} {text}")
    except Exception as e:
        logger.error(f"[GNews] Exception during fetch: {e}")

    return results

