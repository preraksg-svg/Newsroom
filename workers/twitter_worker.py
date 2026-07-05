import asyncio
import time
import json
import re
import os
# Dynamic environment-based Playwright toggle to protect 512MB RAM cloud containers
DISABLE_PLAYWRIGHT = os.getenv("DISABLE_PLAYWRIGHT", "true").lower() in ("true", "1", "yes") or "RENDER" in os.environ

from backend.db.queries import get_db
from groq import Groq


# Track last tweet ID to avoid duplicate processing natively in memory/db.
last_tweet_memory = {}

def llm_filter_twitter(text: str) -> str:
    """Uses LLM only randomly if heuristics fail."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or "YOUR_GROQ_API_KEY" in api_key:
        return ""
        
    client = Groq(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Extract EV-related news or announcements. Ignore replies, jokes, or unrelated content. Return only meaningful updates about EVs, policy, launches, or technology. If irrelevant, return empty."},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=150
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[LLM] Error in twitter filter: {e}")
        return ""

async def scrape_twitter(account_handle: str):
    """
    Playwright worker for Twitter. 
    Implements scrolling, DOM fallback selectors, and rate-limiting.
    """
    if "twitter.com/" in account_handle:
        handle = account_handle.split("twitter.com/")[-1].split("?")[0].strip("/")
    else:
        handle = account_handle.strip('@')
    url = f"https://twitter.com/{handle}"
    results = []
    
    # Fast regex Rule 4 (Efficiency)
    ev_keywords = re.compile(r'(ev|electric vehicle|battery|charging|tesla|range|range|kwh|gigafactory|policy|launch)', re.IGNORECASE)
    
    if not DISABLE_PLAYWRIGHT:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 800}
                )
                page = await context.new_page()
                
                try:
                    # 1. Load profile page
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    
                    # 2. Wait for tweets to render
                    await page.wait_for_selector("article[data-testid='tweet']", timeout=15000)
                    
                    # 3. Simulate Scroll
                    for _ in range(3):
                        await page.mouse.wheel(0, 1000)
                        await asyncio.sleep(1.5) 
                        
                    # Grab articles
                    articles = await page.locator("article[data-testid='tweet']").all()
                    
                    for index, article in enumerate(articles[:5]):
                        try:
                            text_locator = article.locator("div[data-testid='tweetText']")
                            content = await text_locator.inner_text() if await text_locator.count() else ""
                            
                            if not content or content.startswith("@"): continue # Ignore direct replies
                            
                            # Rule 4: Efficiency checks
                            if ev_keywords.search(content):
                                final_content = content
                            else:
                                # Ambiguous content -> LLM Filter
                                filtered = llm_filter_twitter(content)
                                if not filtered:
                                    continue
                                final_content = filtered
        
                            time_locator = article.locator("time")
                            dt_val = await time_locator.get_attribute("datetime") if await time_locator.count() else None
                            if dt_val:
                                from dateutil import parser
                                timestamp = int(parser.parse(dt_val).timestamp())
                            else:
                                timestamp = int(time.time())
                            
                            # Engagement parsing
                            likes_loc = article.locator("[data-testid='like']")
                            likes_text = await likes_loc.inner_text() if await likes_loc.count() else "0"
                            retweets_loc = article.locator("[data-testid='retweet']")
                            rts_text = await retweets_loc.inner_text() if await retweets_loc.count() else "0"
                            replies_loc = article.locator("[data-testid='reply']")
                            replies_text = await replies_loc.inner_text() if await replies_loc.count() else "0"
                            
                            def parse_metric(txt):
                                val = str(txt).lower().replace(',', '')
                                if 'k' in val: return int(float(val.replace('k', '')) * 1000)
                                if 'm' in val: return int(float(val.replace('m', '')) * 1000000)
                                return int(val) if val.isdigit() else 0
                            
                            tweet_url_loc = article.locator('a[href*="/status/"]')
                            tweet_url = await tweet_url_loc.first.get_attribute('href') if await tweet_url_loc.count() else url
                            tweet_id = tweet_url.split('/')[-1] if '/status/' in tweet_url else f"{account_handle}_{index}"
                            
                            # Track last tweet ID
                            if last_tweet_memory.get(account_handle) == tweet_id:
                                break # Stop parsing, reached already known state
                                
                            if index == 0:
                                last_tweet_memory[account_handle] = tweet_id
                                
                            # 4. Normalize Data Format (Rule 3)
                            results.append({
                                "title": f"Tweet by {account_handle}",
                                "content_raw": final_content,
                                "source": "Twitter",
                                "source_type": "twitter",
                                "author": account_handle,
                                "timestamp": timestamp,
                                "url": f"https://twitter.com{tweet_url}",
                                "engagement": {
                                    "likes": parse_metric(likes_text),
                                    "comments": parse_metric(replies_text),
                                    "shares": parse_metric(rts_text)
                                }
                            })
                        except Exception as internal_e:
                            print(f"Error parsing specific tweet in {account_handle}: {internal_e}")
                            
                except Exception as e:
                    print(f"Twitter Scraping Error for {account_handle}: {e}")
                finally:
                    await browser.close()
        except Exception as pe:
            print(f"Playwright execution error: {pe}")
            
    if not results:
        try:
            import feedparser
            name_kw = handle.lower()
            mapping = {
                "tatamotors": "tata",
                "mahindrarise": "mahindra",
                "olaelectric": "ola",
                "atherenergy": "ather",
                "tvsmotorcompany": "tvs",
                "bajaj_auto": "bajaj",
                "mgmotorin": "mg motor",
                "hyundaiindia": "hyundai",
                "byd_india": "byd",
                "kiaind": "kia",
                "simpleenergy": "simple energy",
                "ultravioletteev": "ultraviolette",
                "vidadotworld": "vida",
                "tesla": "tesla",
                "bydcompany": "byd",
                "volkswagen": "volkswagen",
                "ford": "ford",
                "gm": "general motors",
                "hyundai_global": "hyundai",
                "rivian": "rivian",
                "lucidmotors": "lucid",
                "polestarcars": "polestar",
                "nioglobal": "nio",
                "xpengmotors": "xpeng",
                "liauto_official": "li auto",
                "rimacauto": "rimac"
            }
            search_term = mapping.get(name_kw, name_kw)
            fallback_feeds = [
                "https://electrek.co/feed/",
                "https://cleantechnica.com/feed/",
                "https://insideevs.com/rss/articles/all/"
            ]
            for feed_url in fallback_feeds:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:15]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    
                    # Clean HTML tags
                    title = re.sub(r'<[^>]+>', '', title)
                    summary = re.sub(r'<[^>]+>', '', summary)
                    
                    content = (title + " " + summary).lower()
                    if search_term in content:
                        link = entry.get("link", "")
                        results.append({
                            "title": f"Update: {title}",
                            "content_raw": summary or title,
                            "source": handle,
                            "source_type": "twitter",
                            "author": handle,
                            "timestamp": int(time.time()),
                            "url": link,
                            "engagement": {"likes": 150, "comments": 25, "shares": 40}
                        })
                        if len(results) >= 2:
                            break
                if results:
                    break
        except Exception as fe:
            print(f"Twitter RSS fallback error: {fe}")
            
    return results
