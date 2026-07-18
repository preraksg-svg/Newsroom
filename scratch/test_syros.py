import sqlite3
import re
from backend.db.queries import DB_PATH
from backend.llm import filter_article, is_india_relevant

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT title, content, url, source_id, source_type, timestamp FROM scraped_raw WHERE title LIKE '%Syros%'")
row = cur.fetchone()
if row:
    title, content, url, source_id, source_type, ts = row
    print("Title:", title)
    print("Content length:", len(content))
    print("is_india_relevant:", is_india_relevant(title, content))
    
    # Heuristics check
    t_lower = title.lower()
    c_lower = content.lower()
    
    blacklist = ["phone", "smartphone", "mobile recharge", "ipl points", "orange cap", "purple cap", 
                 "cricket score", "recharge plan", "realme", "redmi", "galaxy", "oneplus", 
                 "xiaomi", "motorola", "iphone", "under 30000", "under 20000", "under 15000", "under 10000"]
    for word in blacklist:
        if word in t_lower or word in c_lower:
            print(f"Heuristic Blacklist hit: '{word}'")
            
    ev_terms = ["ev", "electric", "battery", "charger", "charging", "tesla", "byd", "gigafactory", 
                "zero-emission", "ola", "ather", "tata", "mahindra", "electrification", "fame",
                "range test", "solid state"]
    has_ev_term = any(term in t_lower or term in c_lower for term in ev_terms)
    print("Has EV term in heuristics:", has_ev_term)
    
    # Process signal logic check
    raw_content = re.sub(r'(\.\.\.\s*|\[\.\.\.\]\s*|Read\s+More\s*\.\.\.\s*|\[Read\s+More\]\s*)$', '', content.strip(), flags=re.IGNORECASE)
    word_count = len(raw_content.split())
    min_words = 15 if source_type in ['twitter', 'reddit', 'instagram', 'facebook', 'youtube', 'Social', 'Video'] else 120
    print(f"Word count: {word_count}, Min required: {min_words}")
    
    # Let's run filter_article
    import asyncio
    async def run_filter():
        return await asyncio.to_thread(filter_article, title, content)
    res = asyncio.run(run_filter())
    print("filter_article result:", res)
else:
    print("Kia Syros article not found in DB.")
conn.close()
