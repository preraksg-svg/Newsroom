import asyncio
from workers.website_worker import scrape_website
import time

async def main():
    res = await scrape_website('https://electrek.co')
    print("Fetched", len(res))
    for r in res:
        age_hours = (time.time() - r['timestamp']) / 3600
        print(f"Title: {r['title'][:40]}, Age: {age_hours:.1f}h")

asyncio.run(main())
