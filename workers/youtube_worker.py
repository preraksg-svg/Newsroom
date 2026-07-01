import feedparser
import time
import requests
import re
import os
import asyncio
from dateutil import parser
from backend.db.queries import get_db, get_yt_memory, update_yt_memory, is_duplicate

async def scrape_youtube(channel_id: str):
    """
    YouTube worker using RSS endpoints natively bypassing rate limits from HTML scraping.
    """
    # Assuming channel_id can be passed as URL or raw ID
    if "youtube.com" in channel_id:
        c_id = channel_id.split('/')[-1]
    else:
        c_id = channel_id
        
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={c_id}"
    results = []
    
    ev_keywords = re.compile(r'(ev|electric|battery|review|launch|tesla|kwh)', re.IGNORECASE)
    
    try:
        # Using loop.run_in_executor for feedparser as it is synchronous
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, rss_url)
        
        for index, entry in enumerate(feed.entries[:5]):
            title = entry.get("title", "")
            content = entry.get("summary", "")
            link = entry.get("link", "")
            author = entry.get("author", c_id)
            
            video_id = entry.get("yt_videoid", link.split("v=")[-1] if "v=" in link else f"yt_{index}")
            
            last_processed_id = get_yt_memory(c_id)
            if last_processed_id == video_id:
                break
                
            if index == 0:
                update_yt_memory(c_id, video_id)
                
            combined = f"{title}\n{content}"
            if ev_keywords.search(combined):
                final_content = combined
            else:
                continue
                
            dt_str = entry.get("published", entry.get("updated", ""))
            try:
                timestamp = int(parser.parse(dt_str).timestamp()) if dt_str else int(time.time())
            except:
                timestamp = int(time.time())
                
            views = entry.get("media_statistics", {}).get("views", 0)
            
            results.append({
                "title": title,
                "content_raw": final_content,
                "source": "YouTube",
                "source_type": "youtube",
                "author": author,
                "timestamp": timestamp,
                "url": link,
                "engagement": {
                    "likes": 0,
                    "comments": 0,
                    "shares": int(views)
                }
            })
    except Exception as e:
        print(f"YouTube Scraping Error for {c_id}: {e}")
        
    if results:
        import hashlib
        import json
        # Run synchronous DB operations in executor to avoid blocking the event loop
        def persist_to_db():
            with get_db() as conn:
                cur = conn.cursor()
                for item in results:
                    story_id = f"yt_{hashlib.md5(item['url'].encode()).hexdigest()[:10]}"
                    if is_duplicate(item["url"], item["title"]):
                        continue

                    cur.execute("""
                        INSERT OR IGNORE INTO stories (
                            id, url, title, original_content, publisher, 
                            published_date, status, sections, images, audio, ai_summary
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        story_id, item["url"], item["title"], item["content_raw"],
                        item["source"], item["timestamp"], "Draft", "[]", "[]", "{}", "{}"
                    ))
                conn.commit()
            return len(results)

        count = await asyncio.get_event_loop().run_in_executor(None, persist_to_db)
        print(f"[youtube_worker] Persisted {count} items to stories table")
            
    return results
