import asyncio
import sys
import os

sys.path.append(os.getcwd())
from workers.website_worker import scrape_website

async def main():
    urls = [
        "https://evreporter.com/feed/",
        "https://www.saurenergy.com/feed",
        "https://mercomindia.com/feed/",
        "https://cleantechnica.com/category/india/feed/"
    ]
    for url in urls:
        print(f"Scraping: {url}")
        res = await scrape_website(url)
        print(f"Results count: {len(res)}")
        if res:
            title_clean = res[0]['title'].encode('ascii', 'ignore').decode('ascii')
            print(f"Sample title (clean): {title_clean}")

if __name__ == "__main__":
    asyncio.run(main())
