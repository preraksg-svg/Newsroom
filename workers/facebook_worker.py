import asyncio
import time
import os
import re
from playwright.async_api import async_playwright
from groq import Groq

last_fb_memory = {}

def llm_filter_facebook(text: str) -> str:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Extract EV-related official updates or announcements. Ignore generic posts. Return empty if irrelevant."},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=200
        )
        return completion.choices[0].message.content.strip()
    except:
        return ""

async def scrape_facebook(page_url: str):
    """
    Playwright mapped Facebook extractor for public pages.
    """
    results = []
    
    ev_keywords = re.compile(r'(ev|electric|charging|announcement|launch|new|subsidy)', re.IGNORECASE)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()
        
        try:
            await page.goto(page_url, wait_until="domcontentloaded", timeout=45000)
            
            # Dismiss login modal if blocking DOM
            try:
                await page.locator("div[aria-label='Close']").click(timeout=3000)
            except:
                pass
                
            await asyncio.sleep(2)
            
            # Target generic article/div structure of posts
            posts = await page.locator("div[role='article']").all()
            
            for index, post in enumerate(posts[:4]):
                try:
                    # Very rough heuristic text dump since FB classes scramble heavily
                    content = await post.inner_text()
                    
                    post_id = f"fb_{page_url}_{index}" # Hard to extract reliable ID without deep DOM inspection
                    
                    if not content or len(content) < 30: continue
                    
                    if ev_keywords.search(content):
                        final_content = content
                    else:
                        filtered = llm_filter_facebook(content)
                        if not filtered: continue
                        final_content = filtered
                    
                    results.append({
                        "title": f"Facebook Post by {page_url.split('/')[-1] or 'Page'}",
                        "content_raw": final_content,
                        "source": "Facebook",
                        "source_type": "facebook",
                        "author": page_url.split('/')[-1],
                        "timestamp": int(time.time()),
                        "url": page_url, # Generic link to page since direct hash is scrambled on unauth
                        "engagement": {
                            "likes": 0,
                            "comments": 0,
                            "shares": 0
                        }
                    })
                except Exception as e:
                    pass
        except Exception as e:
            print(f"Facebook Scraping Error for {page_url}: {e}")
        finally:
            await browser.close()
            
    return results
