import asyncio
import importlib
import sys
import os
sys.path.insert(0, os.getcwd())

# Force reimport to pick up our latest edits
import workers.website_worker as ww
importlib.reload(ww)

async def main():
    # Use a real valid overdrive article
    test_urls = [
        'https://www.overdrive.in/news-cars/jsw-mg-unveils-adapt-platform-plans-ev-and-phev-launch-by-fy27/',
        'https://www.autocarindia.com/car-news/jsw-mg-to-launch-electric-and-phev-suv-in-august-2026-440101',
    ]
    for url in test_urls:
        print(f"\n--- Testing direct page: {url[:60]} ---")
        content = await ww.scrape_single_article_page(url)
        if content:
            print(f"[OK] Content length: {len(content)} chars")
            print(content[:600])
        else:
            print("[FAIL] NO CONTENT EXTRACTED")

    # Full scraper test for Indian sources  
    print("\n\n=== Full scraper test ===")
    sources = [
        'https://www.overdrive.in',
        'https://www.autocarindia.com',
        'https://auto.ndtv.com',
        'https://www.zigwheels.com',
        'https://www.motoroctane.com',
    ]
    for src in sources:
        try:
            res = await ww.scrape_website(src)
            print(f"\n[{src}] => {len(res)} articles")
            for r in res[:2]:
                print(f"  - {r['title'][:70]}")
        except Exception as e:
            print(f"\n[{src}] ERROR: {type(e).__name__}: {e}")

asyncio.run(main())
