import asyncio
import time
import os
import re
from playwright.async_api import async_playwright
from groq import Groq

last_ig_memory = {}

def llm_filter_instagram(text: str) -> str:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Extract EV announcements or product updates from captions. Ignore lifestyle or irrelevant content. Return empty if irrelevant."},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=150
        )
        return completion.choices[0].message.content.strip()
    except:
        return ""

async def scrape_instagram(account_link: str):
    """
    Playwright mapped Instagram extractor targeting public profile grid structures.
    """
    results = []
    
    # Fast regex Rule 4 (Efficiency)
    ev_keywords = re.compile(r'(ev|electric|charging|battery|range)', re.IGNORECASE)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()
        
        try:
            await page.goto(account_link, wait_until="domcontentloaded", timeout=45000)
            
            # Dismiss login modal if present implicitly by waiting and clicking outside if needed. We assume we can read public page top posts.
            await asyncio.sleep(3)
            
            # Instagram public pages render articles in `a` tags starting with /p/
            posts = await page.locator("a[href^='/p/']").all()
            
            for index, post in enumerate(posts[:3]):
                try:
                    rel_url = await post.get_attribute("href")
                    post_id = rel_url.split('/')[2]
                    
                    if last_ig_memory.get(account_link) == post_id:
                        break
                    if index == 0:
                        last_ig_memory[account_link] = post_id
                        
                    # Extract image alt text which often contains the caption on public grid
                    img_loc = post.locator("img")
                    caption = await img_loc.first.get_attribute("alt") if await img_loc.count() else ""
                    
                    if not caption: continue
                    
                    if ev_keywords.search(caption):
                        final_content = caption
                    else:
                        filtered = llm_filter_instagram(caption)
                        if not filtered: continue
                        final_content = filtered
                    
                    # Engagement cannot reliably be grabbed from grid without clicking. We leave it 0 to avoid login walls on popup.
                    results.append({
                        "title": f"Instagram Post by {account_link.split('/')[-1] or 'User'}",
                        "content_raw": final_content,
                        "source": "Instagram",
                        "source_type": "instagram",
                        "author": account_link.split('/')[-1],
                        "timestamp": int(time.time()),
                        "url": f"https://instagram.com{rel_url}",
                        "engagement": {
                            "likes": 0,
                            "comments": 0,
                            "shares": 0
                        }
                    })
                except Exception as e:
                    pass
        except Exception as e:
            print(f"Instagram Scraping Error for {account_link}: {e}")
        finally:
            await browser.close()
            
    return results
