import os
import time
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dateutil import parser
import logging

logger = logging.getLogger("newsdata_worker")
_executor = ThreadPoolExecutor(max_workers=4)


async def scrape_newsdata(domain_or_query: str):
    """
    Worker using NewsData.io API to fetch EV news.
    """
    results = []
    
    api_key = os.environ.get("NEWS_DATA_API_KEY")
    if not api_key:
        logger.warning("[NewsData] NEWS_DATA_API_KEY not found in environment. Skipping.")
        return results

    if domain_or_query in ["newsapi", "newsdata", "gnews", "newsdata_global", "newsdata_india"]:
        is_global = "global" in domain_or_query.lower() or domain_or_query == "newsdata"
        domain_or_query = ""
    else:
        is_global = True

    # Determine if we are querying a specific domain or general topics
    query = f"site:{domain_or_query}" if (domain_or_query and "." in domain_or_query and " " not in domain_or_query) else ("electric vehicle India OR EV India" if not is_global else "electric vehicle OR EV")
    params = {
        "apikey": api_key,
        "q": query,
        "language": "en",
        "size": 10  # Free tier max is 10
    }
    if not is_global:
        params["country"] = "in"

    url = "https://newsdata.io/api/1/news"
    
    try:
        import requests
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(_executor, lambda: requests.get(url, params=params, timeout=25))
        if response.status_code == 200:
            data = response.json()
            articles = data.get("results", [])
            
            for article in articles:
                content = article.get("content") or article.get("description")
                if not content:
                    continue
                    
                title = article.get("title", "")
                link = article.get("link", "")
                source_name = article.get("source_id", "NewsData")
                author = article.get("creator") 
                author = author[0] if author and isinstance(author, list) else source_name
                
                dt_str = article.get("pubDate", "")
                try:
                    timestamp = int(parser.parse(dt_str).timestamp()) if dt_str else int(time.time())
                except:
                    timestamp = int(time.time())
                    
                results.append({
                    "title": title,
                    "content_raw": content,
                    "source": source_name,
                    "source_type": "newsdata",
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
            logger.error(f"[NewsData] Error fetching data: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"[NewsData] Exception during fetch: {e}")

    return results

