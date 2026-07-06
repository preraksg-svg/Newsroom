import asyncio
import sys
import os

# Add root directory to sys.path
sys.path.append(os.getcwd())

from workers.twitter_worker import scrape_twitter

async def test():
    url = "https://twitter.com/TataMotors"
    print(f"Running scrape_twitter for {url}...")
    try:
        results = await scrape_twitter(url)
        print(f"Scrape completed. Found {len(results)} items.")
        for r in results:
            print(f"- {r['title']}: {r['content_raw'][:100]}...")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test())
