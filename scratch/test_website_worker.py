import asyncio
import sys
import os

sys.path.append(os.getcwd())

from workers.website_worker import scrape_website

async def test():
    url = "https://electrek.co/feed/"
    print(f"Testing scrape_website for {url}...")
    results = await scrape_website(url)
    print(f"Results fetched: {len(results)}")
    for r in results:
        print(f"- {r['title']}")

if __name__ == "__main__":
    asyncio.run(test())
