import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dateutil import parser
import logging

logger = logging.getLogger("newsapi_worker")
_executor = ThreadPoolExecutor(max_workers=4)


async def scrape_newsapi(domain_or_query: str):
    """
    Worker using NewsAPI.ai to fetch clean, structured EV news.
    Uses the newsapi.ai endpoint which matches the UUID-format key in .env.
    """
    results = []
    
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        logger.warning("[NewsAPI] NEWS_API_KEY not found in environment. Skipping.")
        return results

    if domain_or_query in ["newsapi", "newsdata", "gnews", "newsapi_global", "newsapi_india"]:
        is_global = "global" in domain_or_query.lower() or domain_or_query == "newsapi"
        domain_or_query = ""
    else:
        is_global = True

    # Use India-focused query for non-global sources
    if is_global:
        query = "electric vehicle OR EV"
    else:
        query = "electric vehicle India OR EV India OR Tata EV OR Ola Electric OR Ather Energy"

    # newsapi.ai endpoint — matches UUID-format keys
    url = "https://eventregistry.org/api/v1/article/getArticles"
    payload = {
        "query": {
            "$query": {
                "$and": [
                    {"$or": [
                        {"conceptUri": "http://en.wikipedia.org/wiki/Electric_vehicle"},
                        {"keyword": query, "keywordLoc": "title,body"}
                    ]},
                    {"lang": "eng"}
                ]
            },
            "$filter": {"forceMaxDataTimeWindow": "31"}
        },
        "resultType": "articles",
        "articlesSortBy": "date",
        "articlesCount": 10,
        "articleBodyLen": -1,
        "apiKey": api_key
    }
    
    # Add country filter for India-focused queries
    if not is_global:
        payload["query"]["$query"]["$and"].append({"locationUri": "http://en.wikipedia.org/wiki/India"})

    try:
        import requests
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(_executor, lambda: requests.post(url, json=payload, timeout=25))
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", {}).get("results", [])
            
            for article in articles:
                content = article.get("body") or article.get("title", "")
                if not content:
                    continue
                    
                title = article.get("title", "")
                link = article.get("url", "")
                source_name = article.get("source", {}).get("title", "NewsAPI")
                author = article.get("authors", [{}])[0].get("name", source_name) if article.get("authors") else source_name
                
                dt_str = article.get("dateTimePub", "")
                try:
                    timestamp = int(parser.parse(dt_str).timestamp()) if dt_str else int(time.time())
                except Exception:
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
            logger.error(f"[NewsAPI] Error fetching data: {response.status_code} {response.text[:300]}")
    except Exception as e:
        logger.error(f"[NewsAPI] Exception during fetch: {e}")

    return results
