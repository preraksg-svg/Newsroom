import os
import time
import aiohttp
import asyncio
from dateutil import parser
import logging

logger = logging.getLogger("newsapi_worker")

async def scrape_newsapi(domain_or_query: str):
    """
    Worker using News API to fetch clean, structured EV news.
    domain_or_query can be a domain (e.g. 'techcrunch.com') or a search query.
    If it's empty, defaults to 'electric vehicle OR EV'.
    """
    results = []
    
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        logger.warning("[NewsAPI] NEWS_API_KEY not found in environment. Skipping.")
        return results

    if domain_or_query in ["newsapi", "newsdata", "gnews"]:
        domain_or_query = ""

    # Determine if we are querying a specific domain or general topics
    if domain_or_query and "." in domain_or_query and " " not in domain_or_query:
        params = {
            "domains": domain_or_query,
            "q": "electric vehicle OR EV",
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": api_key,
            "pageSize": 10
        }
    else:
        query = domain_or_query if domain_or_query else "electric vehicle OR EV"
        params = {
            "q": query,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": api_key,
            "pageSize": 10
        }

    url = "https://newsapi.org/v2/everything"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get("articles", [])
                    
                    for article in articles:
                        # Require content
                        content = article.get("content") or article.get("description")
                        if not content:
                            continue
                            
                        title = article.get("title", "")
                        link = article.get("url", "")
                        source_name = article.get("source", {}).get("name", "NewsAPI")
                        author = article.get("author") or source_name
                        
                        dt_str = article.get("publishedAt", "")
                        try:
                            timestamp = int(parser.parse(dt_str).timestamp()) if dt_str else int(time.time())
                        except:
                            timestamp = int(time.time())
                            
                        results.append({
                            "title": title,
                            "content_raw": content,
                            "source": source_name,
                            "source_type": "newsapi",
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
                    logger.error(f"[NewsAPI] Error fetching data: {response.status} {text}")
    except Exception as e:
        logger.error(f"[NewsAPI] Exception during fetch: {e}")

    return results

