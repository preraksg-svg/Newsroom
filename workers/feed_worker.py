import feedparser
import requests
import json
import time
from email.utils import parsedate_to_datetime

def table_to_markdown(table_tag):
    rows = table_tag.find_all('tr')
    if not rows:
        return ""
    
    markdown_rows = []
    
    # Extract headers
    headers = []
    first_row_cells = rows[0].find_all(['th', 'td'])
    for cell in first_row_cells:
        headers.append(cell.get_text(" ", strip=True))
        
    if not headers or all(h == "" for h in headers):
        return ""
        
    markdown_rows.append("| " + " | ".join(headers) + " |")
    markdown_rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    # Process remaining rows
    start_idx = 1 if rows[0].find('th') or len(rows) > 1 else 0
    for row in rows[start_idx:]:
        cells = row.find_all(['th', 'td'])
        if not cells:
            continue
        row_data = []
        for cell in cells:
            row_data.append(cell.get_text(" ", strip=True))
        # Ensure row has same number of columns
        if len(row_data) < len(headers):
            row_data.extend([""] * (len(headers) - len(row_data)))
        elif len(row_data) > len(headers):
            row_data = row_data[:len(headers)]
        markdown_rows.append("| " + " | ".join(row_data) + " |")
        
    return "\n" + "\n".join(markdown_rows) + "\n"

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
                        for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'table']):
                            if tag.name == 'table':
                                table_md = table_to_markdown(tag)
                                if table_md:
                                    structured_content.append({"tag": "table", "text": table_md})
                                continue
                            clean_text = tag.get_text(" ", strip=True)
                            is_li = tag.name == 'li'
                            min_len = 20 if tag.name != 'li' else 1
                            
                            # Enhanced noise filter: skip nav/social share noise for li items
                            import re as _re
                            SOCIAL_NAV_NOISE = _re.compile(
                                r'^(home|car news|bike news|facebook|twitter|whatsapp|telegram|linkedin|instagram|youtube|share|email|print|pinterest|reddit|tumblr|rss|menu|search|sign in|log in|login|register|about|contact|advertise|terms|sitemap|back to top|next|previous|more|tags|categories|topics|source|author|editors|copy link|opens in new window)$',
                                _re.IGNORECASE
                            )
                            is_nav_noise = is_li and (
                                SOCIAL_NAV_NOISE.match(clean_text.strip()) or
                                'opens in new window' in clean_text.lower() or
                                (len(clean_text.split()) <= 2 and not any(c.isdigit() for c in clean_text))
                            )
                            if is_nav_noise:
                                continue
                                
                            if len(clean_text) > min_len: 
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
