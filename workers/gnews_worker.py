import os
import time
import requests
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

    if domain_or_query in ["newsapi", "newsdata", "gnews"]:
        domain_or_query = ""

    query = domain_or_query if domain_or_query else "electric vehicle OR EV"
    params = {
        "apikey": api_key,
        "q": query,
        "lang": "en",
        "max": 10
    }

    url = "https://gnews.io/api/v4/search"
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.get(url, params=params, timeout=10))
        
        if response.status_code == 200:
            data = response.json()
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
            logger.error(f"[GNews] Error fetching data: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"[GNews] Exception during fetch: {e}")

    return results
