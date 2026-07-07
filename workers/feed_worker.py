import feedparser
import requests
import json
import time
from email.utils import parsedate_to_datetime

async def scrape_feed(url: str, source_type: str):
    """
    Worker for RSS and API endpoints. Fits identically into the normalizer.
    source_type should be one of "rss", "news_rss", "reddit_json"
    """
    results = []
    
    try:
        if source_type in ["rss", "news_rss"]:
            # Parse RSS Feed
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                publisher = feed.feed.get("title", "Unknown Publisher")
                
                # Rule 7: ORIGINAL NEWS PARSING (Structured Format, No Raw <p> Dumping)
                structured_content = []
                try:
                    article_req = requests.get(link, timeout=5, headers={"User-Agent": "ZapwayNewsroom bot/1.0"})
                    if article_req.status_code == 200:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(article_req.text, 'html.parser')
                        for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
                            clean_text = tag.get_text(" ", strip=True)
                            if len(clean_text) > 20: 
                                structured_content.append({"tag": tag.name, "text": clean_text})
                except Exception as e:
                    print(f"Failed to extract structured HTML from {link}: {e}")
                
                # Fallback to summary if completely blocked
                if not structured_content:
                    summary = entry.get("summary", "")
                    from bs4 import BeautifulSoup
                    clean_summary = BeautifulSoup(summary, 'html.parser').get_text(" ", strip=True) if summary else ""
                    structured_content.append({"tag": "p", "text": clean_summary})

                content_raw = json.dumps(structured_content)
                
                dt_str = entry.get("published", entry.get("updated", ""))
                try:
                    timestamp = int(parsedate_to_datetime(dt_str).timestamp()) if dt_str else int(time.time())
                except:
                    timestamp = int(time.time())
                    
                results.append({
                    "title": title,
                    "content_raw": content_raw,
                    "source": publisher,
                    "timestamp": timestamp,
                    "url": link,
                    "type": source_type,
                    "engagement": {}
                })
                
        elif source_type == "reddit_json":
            # Direct API request without playwright (no key needed)
            headers = {"User-Agent": "ZapwayNewsroom bot/1.0"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                children = data.get("data", {}).get("children", [])
                for child in children[:5]:
                    post = child.get("data", {})
                    results.append({
                        "title": post.get("title", ""),
                        "content_raw": json.dumps([{"tag": "p", "text": post.get("selftext", "")}]),
                        "source": "Reddit",
                        "timestamp": int(post.get("created_utc", time.time())),
                        "url": f"https://reddit.com{post.get('permalink', '')}",
                        "type": "reddit",
                        "engagement": {"upvotes": post.get("score", 0), "comments": post.get("num_comments", 0)}
                    })
    except Exception as e:
        print(f"Feed Scraping Error for {url}: {e}")
        
    return results
