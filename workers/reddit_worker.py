import requests
import time
import os
import re
from groq import Groq

last_reddit_memory = {}

def llm_filter_reddit(text: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or "YOUR_GROQ_API_KEY" in api_key:
        return ""
        
    client = Groq(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Identify early EV signals, leaks, or discussions. Ignore low-value chatter. Extract only useful insights. Return empty if just chatter."},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=150
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[LLM] Error in reddit filter: {e}")
        return ""

async def scrape_reddit(subreddit_url: str):
    """
    Reddit Worker directly fetching .json limits bypass.
    """
    results = []
    
    headers = {"User-Agent": "ZapwayNewsroom bot/1.0"}
    
    # Ensure json mapping format
    if not subreddit_url.endswith(".json"):
        subreddit_url = subreddit_url.rstrip("/") + "/new.json"
        
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.get(subreddit_url, headers=headers, timeout=10))
        if response.status_code == 200:
            data = response.json()

            children = data.get("data", {}).get("children", [])
            
            for index, child in enumerate(children[:10]):
                post = child.get("data", {})
                post_id = post.get("id", "")
                
                if last_reddit_memory.get(subreddit_url) == post_id:
                    break
                if index == 0:
                    last_reddit_memory[subreddit_url] = post_id
                    
                upvotes = post.get("score", 0)
                comments = post.get("num_comments", 0)
                
                # Rule 4: Efficiency pre-filter. Skip extremely low value posts if they're chatter
                if upvotes < 5 and comments < 2:
                    # Might be spam, wait for validation
                    continue
                    
                title = post.get("title", "")
                content = post.get("selftext", "")
                combined = f"{title}\n{content}"
                
                ev_keywords = re.compile(r'(leak|spy|gigafactory|update|software|battery)', re.IGNORECASE)
                if ev_keywords.search(combined) and upvotes > 50:
                    final_content = combined
                else:
                    filtered = llm_filter_reddit(combined)
                    if not filtered: continue
                    final_content = filtered
                
                results.append({
                    "title": title,
                    "content_raw": final_content,
                    "source": "Reddit",
                    "source_type": "reddit",
                    "author": post.get("author", "anonymous"),
                    "timestamp": int(post.get("created_utc", time.time())),
                    "url": f"https://reddit.com{post.get('permalink', '')}",
                    "engagement": {
                        "likes": upvotes,
                        "comments": comments,
                        "shares": 0
                    }
                })
    except Exception as e:
        print(f"Reddit Scraping Error for {subreddit_url}: {e}")
        
    return results
