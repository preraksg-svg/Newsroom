import asyncio
import sys
import os

# Add root to sys.path
sys.path.append(os.getcwd())

from scraper_manager import start_scraping_engine

if __name__ == "__main__":
    print("Direct launch of Scraper Engine...")
    try:
        asyncio.run(start_scraping_engine())
    except KeyboardInterrupt:
        print("Shutdown.")
    except Exception as e:
        print(f"CRASH: {e}")
